PAPER_STEPS = [
    {
        "id": 1,
        "title": "The Problem",
        "subtitle": "Why supply chains fail",
        "concept": "Traditional supply chains suffer from the Bullwhip Effect — small fluctuations in customer demand get amplified at each upstream tier, causing oscillating overstock and stockouts. This happens because each node orders independently without visibility into the full chain.",
        "key_insight": "A 10% swing in retail demand can cause a 40%+ swing in manufacturer orders — purely from information delays and local decision-making across four stages.",
        "what_to_observe": "The simulation resets to initial inventories (12–18 units per stage). Without smart ordering, inventory will diverge wildly as demand fluctuates.",
        "simulation_action": "reset",
        "highlight": "overview"
    },
    {
        "id": 2,
        "title": "The Architecture",
        "subtitle": "4-stage Beer Game (paper Table 2)",
        "concept": "InvAgent models a 4-stage Beer Game: Customer → Retailer → Wholesaler → Distributor → Manufacturer. Each agent only sees its own inventory, backlog, upstream backlog, and in-pipeline orders. No agent can see the others' state directly.",
        "key_insight": "The paper's key design choice: agents are information-constrained on purpose, mirroring real-world supply chains where full visibility across tiers is rare.",
        "what_to_observe": "Look at the four agent cards. Each shows its own inventory, backlog, and in-pipeline units. Upstream stages see the orders that flow up from downstream.",
        "simulation_action": "observe",
        "highlight": "agents"
    },
    {
        "id": 3,
        "title": "5 Demand Scenarios",
        "subtitle": "Table 2 of the paper",
        "concept": "The paper evaluates agents across five demand regimes: Constant (d=4), Variable U(0,4), Larger U(0,8), Seasonal (d=4 then U(5,8) after period 5), and Normal N(4,4). Use the scenario selector at the top to switch between them.",
        "key_insight": "Each scenario has different initial inventories, lead times, capacities, and cost structures. The 'Normal' scenario is the hardest — asymmetric lead times (1–4) and different capacities per stage.",
        "what_to_observe": "Switch to 'Seasonal' and step through periods. At period 5 the demand jumps from 4 to U(5,8) — watch how agent inventories react to the shock.",
        "simulation_action": "observe",
        "highlight": "scenario"
    },
    {
        "id": 4,
        "title": "Chain-of-Thought",
        "subtitle": "How agents reason (paper Figure 4)",
        "concept": "Each agent receives its state as a natural-language prompt and reasons step by step before committing an order. The prompt includes: inventory, backlog, upstream backlog, pipeline, sales history, lead time, and capacity. The agent replies with a plain-text explanation ending in [N].",
        "key_insight": "The bracket format [N] keeps LLM responses unambiguous and easy to parse. No JSON, no structured output — just a number the agent commits to at the end of its reasoning.",
        "what_to_observe": "After this step runs, read the Chain-of-Thought boxes on each of the four agent cards. You can follow exactly why each agent ordered what it did.",
        "simulation_action": "step",
        "highlight": "reasoning"
    },
    {
        "id": 5,
        "title": "Lead Times & Pipeline",
        "subtitle": "The coordination challenge",
        "concept": "Orders don't arrive instantly. In the default scenarios all stages have a 2-period lead time; in the Normal scenario lead times are 1, 2, 3, 4 (retailer to manufacturer). Agents must order ahead while avoiding over-ordering on uncertain demand.",
        "key_insight": "Lead time is the root cause of the bullwhip effect. Longer pipelines mean more uncertainty, so agents over-order as a buffer — amplifying swings at each upstream stage.",
        "what_to_observe": "Watch the 'pipeline' values on each card. Units queued in the pipeline represent committed spending that hasn't arrived yet — agents must factor this in.",
        "simulation_action": "step",
        "highlight": "transit"
    },
    {
        "id": 6,
        "title": "Reward Structure",
        "subtitle": "What gets optimised (paper Section 3)",
        "concept": "Each period: reward = sales_price × sales − order_cost × order − holding × inventory − backlog_cost × backlog. For simple scenarios (Constant/Variable) prices and order costs are zero, so the objective is purely cost minimisation. For Larger/Seasonal/Normal, revenue matters too.",
        "key_insight": "Holding cost = 1 and backlog cost = 1 for all stages in all scenarios. The cost structure is symmetric — unlike the 2:5 ratio in older Beer Game formulations.",
        "what_to_observe": "Watch Total Reward for each stage. Stages that over-order pay holding costs; stages that under-order accumulate backlog costs. Run all 12 periods to see the final comparison.",
        "simulation_action": "step",
        "highlight": "costs"
    },
    {
        "id": 7,
        "title": "Baseline Comparison",
        "subtitle": "LLM vs. Base-Stock vs. Tracking-Demand",
        "concept": "The paper compares LLM agents against two classical heuristics. Base-Stock: order enough to bring inventory position up to capacity. Tracking-Demand: order to cover average recent sales × lead time. After the 12-period episode completes, the results panel shows all three side by side.",
        "key_insight": "InvAgent shows that LLMs match or beat classical baselines without any domain-specific training — especially in stochastic demand scenarios where fixed-rule policies struggle.",
        "what_to_observe": "Run all 12 periods then view the Results panel below. Compare LLM total reward vs. Base-Stock and Tracking-Demand across all four stages. Switch scenarios and run again to see how the gap changes.",
        "simulation_action": "observe",
        "highlight": "results"
    }
]
