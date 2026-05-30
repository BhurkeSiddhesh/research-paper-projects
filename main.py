from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Global state
env = None
retailer_agent = None
distributor_agent = None

@app.post("/api/reset")
def reset_simulation():
    global env, retailer_agent, distributor_agent
    env = SupplyChainEnv()
    retailer_agent = LLMAgent(role="Retailer", use_mock=True)
    distributor_agent = LLMAgent(role="Distributor", use_mock=True)
    return {"status": "success", "state": env.get_state()}

@app.post("/api/step")
def step_simulation():
    global env, retailer_agent, distributor_agent
    if env is None:
        reset_simulation()
        
    state = env.get_state()

    # Merge time into node states so agents can reference it in their prompts
    retailer_state = {**state["retailer"], "time": state["time"]}
    distributor_state = {**state["distributor"], "time": state["time"]}

    # 1. Retailer Agent decides order quantity based on its state
    retailer_decision = retailer_agent.generate_order_decision(retailer_state)

    # 2. Distributor Agent decides order quantity based on its state
    distributor_decision = distributor_agent.generate_order_decision(distributor_state)
    
    # 3. Environment steps forward using the decisions
    step_result = env.step_refined(retailer_decision["order_quantity"], distributor_decision["order_quantity"])
    
    return {
        "status": "success",
        "state": env.get_state(),
        "decisions": {
            "retailer": retailer_decision,
            "distributor": distributor_decision
        },
        "step_details": step_result
    }

@app.get("/api/state")
def get_state():
    global env
    if env is None:
        reset_simulation()
    return {"state": env.get_state()}

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
        retailer_agent = LLMAgent(role="Retailer", use_mock=True)
        distributor_agent = LLMAgent(role="Distributor", use_mock=True)

    elif step["simulation_action"] == "step":
        if env is None:
            env = SupplyChainEnv()
            retailer_agent = LLMAgent(role="Retailer", use_mock=True)
            distributor_agent = LLMAgent(role="Distributor", use_mock=True)
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
            "decisions": {
                "retailer": retailer_decision,
                "distributor": distributor_decision
            },
            "step_details": step_details
        }

    else:  # observe — no sim change
        if env is None:
            env = SupplyChainEnv()
            retailer_agent = LLMAgent(role="Retailer", use_mock=True)
            distributor_agent = LLMAgent(role="Distributor", use_mock=True)

    return {
        "step": step,
        "state": env.get_state(),
        "sim_result": sim_result
    }

# Serve frontend static files — must come after all /api routes
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
