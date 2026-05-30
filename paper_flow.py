PAPER_STEPS = [
    {
        "id": 1,
        "title": "The Problem",
        "subtitle": "Why supply chains fail",
        "concept": "Traditional supply chains suffer from the Bullwhip Effect — small fluctuations in customer demand get amplified at each upstream tier, causing oscillating overstock and stockouts. This happens because each node orders independently without visibility into the full chain.",
        "key_insight": "A 10% swing in retail demand can cause a 40%+ swing in distributor orders — purely from information delays and local decision-making.",
        "what_to_observe": "Notice the simulation starts with inventory=50 at both nodes. Without smart ordering, this will diverge wildly as customer demand fluctuates.",
        "simulation_action": "reset",
        "highlight": "overview"
    },
    {
        "id": 2,
        "title": "The Architecture",
        "subtitle": "A 3-tier Beer Game",
        "concept": "InvAgent models the classic Beer Game: Customer → Retailer → Distributor → Supplier. Each tier can only see its own inventory, backlog, and in-transit orders. No tier can see what the others are doing in real time.",
        "key_insight": "The paper's key design choice: agents are information-constrained on purpose, mirroring real-world supply chains where full visibility is rare.",
        "what_to_observe": "Look at the three nodes: Retailer (faces customer demand directly), Distributor (faces Retailer's orders), and Supplier (infinite capacity, 2-step lead time).",
        "simulation_action": "observe",
        "highlight": "agents"
    },
    {
        "id": 3,
        "title": "Chain-of-Thought",
        "subtitle": "How agents reason",
        "concept": "Instead of a lookup table or optimizer, each agent is given its current state as a prompt and asked to reason step by step: What is my inventory position? What demand do I anticipate? How much is already in transit? How much should I order?",
        "key_insight": "CoT prompting turns the ordering decision into interpretable reasoning — you can read WHY the agent ordered what it did, not just what it ordered.",
        "what_to_observe": "After this step runs, read the LLM Chain-of-Thought boxes on each agent card. You can follow the agent's logic directly.",
        "simulation_action": "step",
        "highlight": "reasoning"
    },
    {
        "id": 4,
        "title": "Lead Times",
        "subtitle": "The coordination challenge",
        "concept": "Orders don't arrive instantly. Retailer waits 1 period for deliveries from Distributor. Distributor waits 2 periods for deliveries from Supplier. Agents must order ahead — but demand is random, so they must also avoid over-ordering.",
        "key_insight": "Lead time is the root cause of the bullwhip effect. A longer pipeline means more uncertainty, so agents tend to over-order as a buffer — amplifying swings upstream.",
        "what_to_observe": "Watch the 'In Transit' values on each card. The Distributor's in-transit grows before inventory does — that's the pipeline the agent must mentally model.",
        "simulation_action": "step",
        "highlight": "transit"
    },
    {
        "id": 5,
        "title": "Cost Structure",
        "subtitle": "What gets optimized",
        "concept": "Performance is measured by total cost. Holding cost penalizes excess inventory (tying up capital). Stockout cost penalizes unmet demand (lost sales + expediting). The Retailer faces higher penalties because it's closest to the customer.",
        "key_insight": "Retailer: $2/unit held, $5/unit short. Distributor: $1/unit held, $4/unit short. Agents must balance these asymmetric costs — holding too much wastes money, holding too little loses customers.",
        "what_to_observe": "Watch the Total Cost metrics in the header grow each step. Costs compound — a bad decision now echoes for multiple periods through the pipeline.",
        "simulation_action": "step",
        "highlight": "costs"
    },
    {
        "id": 6,
        "title": "Emergent Coordination",
        "subtitle": "No communication needed",
        "concept": "Neither agent tells the other what it's doing. Yet through independent CoT reasoning on their own local state, they achieve coordinated behaviour — the Distributor anticipates the Retailer's needs without being told. This emergent coordination is the paper's central claim.",
        "key_insight": "The paper shows LLM agents reduce total supply chain cost by ~15-20% vs. naive heuristics, without adding any communication channel between nodes.",
        "what_to_observe": "Look at the Workflow Trace panel. You can see exactly when the Distributor fulfills the Retailer's order and when that shipment enters transit — coordination happening implicitly.",
        "simulation_action": "step",
        "highlight": "workflow"
    },
    {
        "id": 7,
        "title": "Key Findings",
        "subtitle": "What the paper concludes",
        "concept": "InvAgent demonstrates that off-the-shelf LLMs (GPT-4, Claude) can manage multi-agent supply chains with near-optimal performance. They adapt to demand shocks without retraining, and their reasoning is fully interpretable — unlike neural or RL-based approaches.",
        "key_insight": "The biggest win: LLM agents don't need domain-specific training data. The supply chain context fits in a prompt. This makes them deployable in new settings immediately.",
        "what_to_observe": "Compare Retailer vs. Distributor total costs over the run. The Retailer typically pays more (higher stockout penalty) — exactly what the paper predicts for the downstream node.",
        "simulation_action": "observe",
        "highlight": "all"
    }
]
