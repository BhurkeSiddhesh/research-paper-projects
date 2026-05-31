from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from environment import SupplyChainEnv, SCENARIOS
from agent import LLMAgent
from baselines import BaseStockPolicy, TrackingDemandPolicy, run_baseline_episode
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

env: Optional[SupplyChainEnv] = None
agents: list = []
current_scenario = "variable"

llm_config = {
    "provider": "mock",
    "api_key": None,
    "base_url": None,
    "model": None,
}

# Cumulative baseline rewards for comparison (populated after episode ends)
baseline_rewards: dict = {}


def make_agents(scenario_name):
    return [
        LLMAgent(role=name, **llm_config)
        for name in ["Retailer", "Wholesaler", "Distributor", "Manufacturer"]
    ]


def ensure_env():
    global env, agents
    if env is None:
        env = SupplyChainEnv(current_scenario)
        agents = make_agents(current_scenario)


# ── Scenario ───────────────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    scenario: str


@app.post("/api/scenario")
def set_scenario(req: ScenarioRequest):
    global env, agents, current_scenario, baseline_rewards
    if req.scenario not in SCENARIOS:
        return {"error": f"Unknown scenario '{req.scenario}'"}
    current_scenario = req.scenario
    env = SupplyChainEnv(current_scenario)
    agents = make_agents(current_scenario)
    baseline_rewards = {}
    return {"status": "ok", "scenario": current_scenario, "state": env.get_state()}


# ── Episode ────────────────────────────────────────────────────────────────

@app.post("/api/episode/start")
def start_episode():
    global env, agents, baseline_rewards
    env = SupplyChainEnv(current_scenario)
    agents = make_agents(current_scenario)
    baseline_rewards = {}
    return {"status": "ok", "state": env.get_state()}


@app.post("/api/episode/step")
def step_episode():
    global env, agents, baseline_rewards
    ensure_env()

    if env.is_done():
        return {"status": "done", "state": env.get_state()}

    state = env.get_state()

    # Build per-agent state dicts (add extra fields agents need)
    agent_states = []
    for s in state["stages"]:
        agent_states.append({**s, "period": state["period"]})

    # LLM decisions
    decisions = [agent.generate_order_decision(s) for agent, s in zip(agents, agent_states)]
    actions = [d["order_quantity"] for d in decisions]

    # Step environment
    result = env.step(actions)

    # On final period, compute baseline comparisons
    if result["is_done"] and not baseline_rewards:
        bs_rewards  = run_baseline_episode(SupplyChainEnv, current_scenario, BaseStockPolicy)
        td_rewards  = run_baseline_episode(SupplyChainEnv, current_scenario, TrackingDemandPolicy)
        llm_rewards = env.total_rewards()
        baseline_rewards = {
            "llm":           llm_rewards,
            "base_stock":    bs_rewards,
            "tracking_demand": td_rewards,
        }

    return {
        "status": "ok",
        "period": result["period"],
        "customer_demand": result["customer_demand"],
        "is_done": result["is_done"],
        "stages": result["stages"],
        "decisions": [
            {"stage": i, "reasoning": d["reasoning"], "order_quantity": d["order_quantity"]}
            for i, d in enumerate(decisions)
        ],
        "workflow_log": result["workflow_log"],
        "baseline_rewards": baseline_rewards if result["is_done"] else None,
    }


@app.get("/api/episode/state")
def get_episode_state():
    ensure_env()
    return {"state": env.get_state()}


@app.get("/api/episode/results")
def get_episode_results():
    ensure_env()
    return {
        "scenario": current_scenario,
        "is_done": env.is_done(),
        "llm_rewards": env.total_rewards(),
        "baseline_rewards": baseline_rewards,
    }


# ── LLM config ─────────────────────────────────────────────────────────────

class LLMConfigRequest(BaseModel):
    provider: str
    api_key:  Optional[str] = None
    base_url: Optional[str] = None
    model:    Optional[str] = None


@app.get("/api/llm/config")
def get_llm_config():
    return {
        "provider": llm_config["provider"],
        "base_url": llm_config["base_url"],
        "model":    llm_config["model"],
        "has_api_key": bool(llm_config["api_key"]),
    }


@app.post("/api/llm/config")
def set_llm_config(req: LLMConfigRequest):
    global llm_config, agents
    llm_config = {
        "provider": req.provider,
        "api_key":  req.api_key  or None,
        "base_url": req.base_url or None,
        "model":    req.model    or None,
    }
    agents = make_agents(current_scenario)
    return {"status": "ok", "provider": req.provider}


@app.post("/api/llm/test")
def test_llm_config():
    test_state = {
        "stage": 0, "name": "Retailer", "period": 1,
        "inventory": 10, "backlog": 2, "upstream_backlog": 0,
        "pipeline": [0, 0], "sales_history": [4, 3, 4],
        "lead_time": 2, "capacity": 20,
    }
    agent = LLMAgent(role="Retailer", **llm_config)
    result = agent.generate_order_decision(test_state)
    error = result["reasoning"].startswith(
        ("Gemini error", "Ollama error", "OpenRouter error", "[LLM parse failed")
    )
    return {
        "ok": not error,
        "provider": llm_config["provider"],
        "reasoning_preview": result["reasoning"][:200],
        "order_quantity": result["order_quantity"],
    }


# ── Paper flow ─────────────────────────────────────────────────────────────

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
    global env, agents
    step = next((s for s in PAPER_STEPS if s["id"] == step_id), None)
    if not step:
        return {"error": "Step not found"}

    sim_result = None
    action = step.get("simulation_action", "observe")

    if action == "reset":
        env = SupplyChainEnv(current_scenario)
        agents = make_agents(current_scenario)
    elif action == "step":
        ensure_env()
        state = env.get_state()
        agent_states = [{**s, "period": state["period"]} for s in state["stages"]]
        decisions = [agent.generate_order_decision(s) for agent, s in zip(agents, agent_states)]
        actions_list = [d["order_quantity"] for d in decisions]
        step_details = env.step(actions_list)
        sim_result = {
            "decisions": [
                {"stage": i, "reasoning": d["reasoning"], "order_quantity": d["order_quantity"]}
                for i, d in enumerate(decisions)
            ],
            "step_details": step_details,
        }
    else:
        ensure_env()

    return {"step": step, "state": env.get_state(), "sim_result": sim_result}


# ── Scenarios list ─────────────────────────────────────────────────────────

@app.get("/api/scenarios")
def list_scenarios():
    return {"scenarios": list(SCENARIOS.keys()), "current": current_scenario}


# Serve frontend — must come after all /api routes
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
