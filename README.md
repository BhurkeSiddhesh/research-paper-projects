# 📚 Research Paper Side Projects

Welcome to the **Research Paper Side Projects** repository! This workspace is dedicated to reproducing, demonstrating, and experimenting with state-of-the-art academic papers in Artificial Intelligence, Multi-Agent Systems, and Optimization.

---

## 🚀 Active Project: InvAgent (arXiv:2407.11384)

> **InvAgent: A Large Language Model based Multi-Agent System for Inventory Management in Supply Chains**
> *Georgia Institute of Technology (WMAC @ AAAI 2025)*
>
> 📄 **Paper Reference:** [arXiv:2407.11384](https://arxiv.org/abs/2407.11384)

InvAgent introduces an autonomous multi-agent system where LLM-powered agents act as supply chain nodes (e.g., Retailers, Distributors) to solve the classic inventory management replenishment problem. By leveraging **Chain-of-Thought (CoT) reasoning**, the agents learn to dynamically optimize ordering decisions—balancing holding costs, backlog penalties, and lead-time delays—under highly volatile demand patterns.

### 🏗️ Codebase Architecture

Our implementation is divided into a robust Python backend simulation and an interactive, modern web-based frontend dashboard:

```mermaid
graph TD
    subgraph Frontend (HTML/CSS/JS Dashboard)
        UI[Glassmorphic Dashboard] <--> |API Calls| App[app.js Controller]
    end

    subgraph Backend (FastAPI Simulation)
        Main[main.py FastAPI App] <--> |Step / Reset| Env[SupplyChainEnv]
        Env <--> |Track State & Cost| NodeR[Retailer Node]
        Env <--> |Track State & Cost| NodeD[Distributor Node]
        Main --> |Prompt State| AgentR[Retailer LLM Agent]
        Main --> |Prompt State| AgentD[Distributor LLM Agent]
    end
    
    Customer[Customer Demand] -.-> |Fulfill| NodeR
    NodeR -.-> |Replenish Order| NodeD
    NodeD -.-> |Replenish Order| Supplier[External Supplier]
```

#### 📦 Backend (`invagent/backend/`)
* **`main.py`**: The FastAPI server exposing HTTP REST endpoints (`/api/state`, `/api/reset`, `/api/step`) to drive the step-by-step supply chain simulation.
* **`environment.py`**: The underlying supply chain engine. Models individual nodes, tracks inventory levels, computes holding and stockout costs, manages lead-time transit schedules, and routes customer demand.
* **`agent.py`**: Implements the `LLMAgent` class. Builds LLM prompts embedded with current inventory states, expects structured JSON output containing step-by-step logic, and has a reliable heuristic target-based fallback for local mock simulation mode.
* **`test_environment.py`**: Unit tests verifying the correctness of node states, replenishment math, and cost calculations.

#### 🎨 Frontend (`invagent/frontend/`)
* **`index.html` & `styles.css`**: A premium, futuristic **glassmorphic dashboard** styled with custom harmonious HSL color palettes and modern typography (`Outfit` from Google Fonts). Responsive and optimized for smooth user interaction.
* **`app.js`**: Drives the live dashboard state. Implements dynamic typing effects for showing the LLMs' Chain-of-Thought reasoning, real-time node state telemetry, and action-triggered simulation steps.

---

## 🔮 Future Project: LLM Optimization Heuristics (arXiv:2503.03350)

> **Leveraging Large Language Models to Develop Heuristics for Emerging Optimization Problems**
> *TU Dortmund University & Karlsruhe Institute of Technology*
>
> 📄 **Paper Reference:** [arXiv:2503.03350](https://arxiv.org/abs/2503.03350)

This paper explores evolutionary frameworks powered by Large Language Models to automatically discover, test, and refine heuristic algorithms for complex, emerging combinatorial optimization problems. It seeks to replace resource-intensive manual heuristic design with LLM-guided evolutionary code generation.

* **Status:** Roadmap. Reference PDF is archived in the workspace for upcoming implementation phases.

---

## 🛠️ How to Run InvAgent

### 1. Prerequisites
Ensure you have Python 3.10+ installed. Install the required Python dependencies:
```bash
pip install fastapi uvicorn pypdf
```

### 2. Start the Backend Server
Navigate to the backend directory and run the FastAPI server via Uvicorn:
```bash
cd invagent/backend
uvicorn main:app --reload --port 8000
```
The server will start on `http://localhost:8000`. You can inspect the interactive OpenAPI docs at `http://localhost:8000/docs`.

### 3. Open the Frontend Dashboard
Simply open the `invagent/frontend/index.html` file in any modern web browser or run a simple local HTTP server:
```bash
# In another terminal window inside invagent/frontend:
python -m http.server 3000
```
Then visit `http://localhost:3000` to interact with the glassmorphic simulation!

---

## 🛡️ Workspace Guidelines & Rules
This project strictly follows the **Durable Agent Constitution**:
* All changes must be tracked in `AGENTS.md` and the `task.md` ledger.
* System updates are audited via `JULES_LOG.json` to prevent regressions.
* Keep the code clean, modular, and tightly matched to the original papers' math and structural assumptions.
