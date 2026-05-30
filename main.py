from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from environment import SupplyChainEnv
from agent import LLMAgent
from paper_flow import PAPER_STEPS

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global state ───────────────────────────────────────────────────────────
env = None
retailer_agent = None
distributor_agent = None

llm_config = {
    "provider": "mock",
    "api_key": None,
    "base_url": None,
    "model": None,
}


def make_agents():
    return (
        LLMAgent(role="Retailer", **llm_config),
        LLMAgent(role="Distributor", **llm_config),
    )


# ── Simulation endpoints ───────────────────────────────────────────────────

@app.post("/api/reset")
def reset_simulation():
    global env, retailer_agent, distributor_agent
    env = SupplyChainEnv()
    retailer_agent, distributor_agent = make_agents()
    return {"status": "success", "state": env.get_state()}


@app.post("/api/step")
def step_simulation():
    global env, retailer_agent, distributor_agent
    if env is None:
        reset_simulation()

    state = env.get_state()
    retailer_state = {**state["retailer"], "time": state["time"]}
    distributor_state = {**state["distributor"], "time": state["time"]}

    retailer_decision = retailer_agent.generate_order_decision(retailer_state)
    distributor_decision = distributor_agent.generate_order_decision(distributor_state)

    step_result = env.step_refined(
        retailer_decision["order_quantity"],
        distributor_decision["order_quantity"]
    )

    return {
        "status": "success",
        "state": env.get_state(),
        "decisions": {
            "retailer": retailer_decision,
            "distributor": distributor_decision,
        },
        "step_details": step_result,
    }


@app.get("/api/state")
def get_state():
    global env
    if env is None:
        reset_simulation()
    return {"state": env.get_state()}


# ── LLM config endpoints ───────────────────────────────────────────────────

class LLMConfigRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


@app.get("/api/llm/config")
def get_llm_config():
    return {
        "provider": llm_config["provider"],
        "base_url": llm_config["base_url"],
        "model": llm_config["model"],
        "has_api_key": bool(llm_config["api_key"]),
    }


@app.post("/api/llm/config")
def set_llm_config(req: LLMConfigRequest):
    global llm_config, retailer_agent, distributor_agent
    llm_config = {
        "provider": req.provider,
        "api_key": req.api_key or None,
        "base_url": req.base_url or None,
        "model": req.model or None,
    }
    # Recreate agents so next step uses new config
    retailer_agent, distributor_agent = make_agents()
    return {"status": "ok", "provider": req.provider}


@app.post("/api/llm/test")
def test_llm_config():
    """Run a single agent decision with dummy state to verify connectivity."""
    test_state = {"inventory": 20, "backlog": 5, "in_transit": 10, "time": 0}
    agent = LLMAgent(role="Retailer", **llm_config)
    result = agent.generate_order_decision(test_state)
    error = result["reasoning"].startswith(("Gemini error", "Ollama error", "OpenRouter error", "[Parse error"))
    return {
        "ok": not error,
        "provider": llm_config["provider"],
        "reasoning_preview": result["reasoning"][:200],
        "order_quantity": result["order_quantity"],
    }


# ── Paper flow endpoints ───────────────────────────────────────────────────

@app.get("/api/paper/steps")
def get_paper_steps():
    return {
        "steps": [
            {"id": s["id"], "title": s["title"], "subtitle": s["subtitle"]}
            for s in PAPER_STEPS
        ]
    }


@app.post("/api/paper/step/{step_id}")
def run_paper_step(step_id: int):
    global env, retailer_agent, distributor_agent
    step = next((s for s in PAPER_STEPS if s["id"] == step_id), None)
    if not step:
        return {"error": "Step not found"}

    sim_result = None

    if step["simulation_action"] == "reset":
        env = SupplyChainEnv()
        retailer_agent, distributor_agent = make_agents()

    elif step["simulation_action"] == "step":
        if env is None:
            env = SupplyChainEnv()
            retailer_agent, distributor_agent = make_agents()
        state = env.get_state()
        retailer_state = {**state["retailer"], "time": state["time"]}
        distributor_state = {**state["distributor"], "time": state["time"]}
        retailer_decision = retailer_agent.generate_order_decision(retailer_state)
        distributor_decision = distributor_agent.generate_order_decision(distributor_state)
        step_details = env.step_refined(
            retailer_decision["order_quantity"],
            distributor_decision["order_quantity"]
        )
        sim_result = {
            "decisions": {"retailer": retailer_decision, "distributor": distributor_decision},
            "step_details": step_details,
        }

    else:  # observe
        if env is None:
            env = SupplyChainEnv()
            retailer_agent, distributor_agent = make_agents()

    return {"step": step, "state": env.get_state(), "sim_result": sim_result}


# Serve frontend — must come after all /api routes
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
