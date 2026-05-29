from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from environment import SupplyChainEnv
from agent import LLMAgent

app = FastAPI()

# Enable CORS for the frontend
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
    
    # 1. Retailer Agent decides order quantity based on its state
    retailer_decision = retailer_agent.generate_order_decision(state["retailer"])
    
    # 2. Distributor Agent decides order quantity based on its state
    distributor_decision = distributor_agent.generate_order_decision(state["distributor"])
    
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
