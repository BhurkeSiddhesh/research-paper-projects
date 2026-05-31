import random
import math

SCENARIOS = {
    "constant": {
        "demand_type": "constant",
        "demand_param": 4,
        "init_inv":    [12, 12, 12, 12],
        "lead_times":  [2,  2,  2,  2],
        "capacity":    [20, 20, 20, 20],
        "sales_price": [0,  0,  0,  0],
        "order_cost":  [0,  0,  0,  0],
        "hold_cost":   [1,  1,  1,  1],
        "backlog_cost":[1,  1,  1,  1],
    },
    "variable": {
        "demand_type": "uniform",
        "demand_param": (0, 4),
        "init_inv":    [12, 12, 12, 12],
        "lead_times":  [2,  2,  2,  2],
        "capacity":    [20, 20, 20, 20],
        "sales_price": [0,  0,  0,  0],
        "order_cost":  [0,  0,  0,  0],
        "hold_cost":   [1,  1,  1,  1],
        "backlog_cost":[1,  1,  1,  1],
    },
    "larger": {
        "demand_type": "uniform",
        "demand_param": (0, 8),
        "init_inv":    [12, 12, 12, 12],
        "lead_times":  [2,  2,  2,  2],
        "capacity":    [20, 20, 20, 20],
        "sales_price": [5,  5,  5,  5],
        "order_cost":  [5,  5,  5,  5],
        "hold_cost":   [1,  1,  1,  1],
        "backlog_cost":[1,  1,  1,  1],
    },
    "seasonal": {
        "demand_type": "seasonal",
        "demand_param": {"low": 4, "high": (5, 8), "switch_t": 5},
        "init_inv":    [12, 12, 12, 12],
        "lead_times":  [2,  2,  2,  2],
        "capacity":    [20, 20, 20, 20],
        "sales_price": [5,  5,  5,  5],
        "order_cost":  [5,  5,  5,  5],
        "hold_cost":   [1,  1,  1,  1],
        "backlog_cost":[1,  1,  1,  1],
    },
    "normal": {
        "demand_type": "normal",
        "demand_param": (4, 2),
        "init_inv":    [12, 14, 16, 18],
        "lead_times":  [1,  2,  3,  4],
        "capacity":    [20, 22, 24, 26],
        "sales_price": [9,  8,  7,  6],
        "order_cost":  [8,  7,  6,  5],
        "hold_cost":   [1,  1,  1,  1],
        "backlog_cost":[1,  1,  1,  1],
    },
}

STAGE_NAMES = ["Retailer", "Wholesaler", "Distributor", "Manufacturer"]
MAX_PERIODS = 12
LMAX = 4  # max lead time across all scenarios (for sales history length)


class SupplyChainNode:
    def __init__(self, stage_idx, scenario_params):
        self.stage_idx = stage_idx
        self.name = STAGE_NAMES[stage_idx]
        self.lead_time   = scenario_params["lead_times"][stage_idx]
        self.capacity    = scenario_params["capacity"][stage_idx]
        self.sales_price = scenario_params["sales_price"][stage_idx]
        self.order_cost  = scenario_params["order_cost"][stage_idx]
        self.hold_cost   = scenario_params["hold_cost"][stage_idx]
        self.backlog_cost = scenario_params["backlog_cost"][stage_idx]

        self.inventory   = scenario_params["init_inv"][stage_idx]
        self.backlog     = 0
        self.upstream_backlog = 0   # units upstream still owes this node
        self.sales_history = []     # units actually sold/fulfilled each period
        # pipeline[i] = quantity arriving after i+1 more periods
        self.pipeline = [0] * self.lead_time

        self.total_reward = 0.0
        self.last_order   = 0
        self.last_sales   = 0


class SupplyChainEnv:
    def __init__(self, scenario_name="variable"):
        self.scenario_name = scenario_name
        self.params = SCENARIOS[scenario_name]
        self.current_period = 0
        self.nodes = [SupplyChainNode(i, self.params) for i in range(4)]
        self._last_demand = None

    # ── Demand generation ──────────────────────────────────────────────────

    def generate_demand(self, t):
        dt = self.params["demand_type"]
        p  = self.params["demand_param"]
        if dt == "constant":
            return int(p)
        if dt == "uniform":
            return random.randint(p[0], p[1])
        if dt == "normal":
            val = random.gauss(p[0], p[1])
            return max(0, round(val))
        if dt == "seasonal":
            if t < p["switch_t"]:
                return int(p["low"])
            lo, hi = p["high"]
            return random.randint(lo, hi)
        return 4

    # ── Episode step ───────────────────────────────────────────────────────

    def step(self, actions):
        """
        actions: list of 4 integers — order quantities for each stage.
        Returns dict with per-stage results and workflow log.
        """
        self.current_period += 1
        t = self.current_period

        # External demand only hits stage 0 (Retailer)
        customer_demand = self.generate_demand(t)
        self._last_demand = customer_demand
        workflow_log = []
        workflow_log.append({
            "phase": "Demand",
            "detail": f"Period {t}: customer demand = {customer_demand} units"
        })

        stage_results = []

        # --- Process upstream → downstream deliveries first ---
        # Each node receives the front of its pipeline
        deliveries = []
        for i, node in enumerate(self.nodes):
            if node.lead_time > 0:
                incoming = node.pipeline[0]
                node.pipeline = node.pipeline[1:] + [0]
            else:
                incoming = 0
            node.inventory += incoming
            deliveries.append(incoming)
            workflow_log.append({
                "phase": f"{node.name}: Receive",
                "detail": f"{incoming} units arrived (pipeline delivery)"
            })

        # --- Fulfill demand stage by stage ---
        # Stage 0 faces customer demand; stage i>0 faces the order from stage i-1
        downstream_orders = [customer_demand] + [
            self.nodes[i].last_order for i in range(3)
        ]

        for i, node in enumerate(self.nodes):
            demand_faced = downstream_orders[i]
            total_needed = demand_faced + node.backlog
            sales = min(node.inventory, total_needed)
            node.inventory -= sales
            node.backlog = total_needed - sales
            node.last_sales = sales
            node.sales_history.append(sales)

            # Capped order
            raw_order = max(0, min(actions[i], node.capacity))
            node.last_order = raw_order

            # Upstream owes what it can't deliver now (tracked as upstream_backlog on requester side)
            # Stage 4 has infinite supplier — always fulfilled immediately pushed into pipeline
            if i == 3:
                fulfillable = raw_order
                node.upstream_backlog = 0
            else:
                upstream = self.nodes[i + 1]
                fulfillable = min(raw_order, upstream.inventory)
                upstream.inventory -= fulfillable
                # Unfulfilled portion becomes upstream_backlog for this node
                node.upstream_backlog = max(0, raw_order - fulfillable)

            # Push fulfillable into this node's pipeline (arrives in lead_time periods)
            if node.lead_time > 0:
                node.pipeline[-1] += fulfillable
            else:
                node.inventory += fulfillable

            # Reward: sales_price * sales - order_cost * order - hold * inv - backlog * backlog
            reward = (
                node.sales_price * sales
                - node.order_cost * raw_order
                - node.hold_cost * node.inventory
                - node.backlog_cost * node.backlog
            )
            node.total_reward += reward

            workflow_log.append({
                "phase": f"{node.name}: Fulfill & Order",
                "detail": (
                    f"Demand {demand_faced} + backlog → sold {sales}, "
                    f"inv {node.inventory}, backlog {node.backlog}; "
                    f"ordered {raw_order} (got {fulfillable}); reward {reward:+.0f}"
                )
            })

            stage_results.append({
                "stage": i,
                "name": node.name,
                "inventory": node.inventory,
                "backlog": node.backlog,
                "upstream_backlog": node.upstream_backlog,
                "pipeline": list(node.pipeline),
                "sales": sales,
                "order": raw_order,
                "reward": reward,
                "total_reward": node.total_reward,
                "sales_history": list(node.sales_history[-LMAX:]),
                "lead_time": node.lead_time,
            })

        return {
            "period": t,
            "customer_demand": customer_demand,
            "is_done": self.is_done(),
            "stages": stage_results,
            "workflow_log": workflow_log,
        }

    # ── Accessors ──────────────────────────────────────────────────────────

    def get_state(self):
        return {
            "period": self.current_period,
            "max_periods": MAX_PERIODS,
            "scenario": self.scenario_name,
            "is_done": self.is_done(),
            "customer_demand": self._last_demand,
            "stages": [
                {
                    "stage": i,
                    "name": node.name,
                    "inventory": node.inventory,
                    "backlog": node.backlog,
                    "upstream_backlog": node.upstream_backlog,
                    "pipeline": list(node.pipeline),
                    "sales_history": list(node.sales_history[-LMAX:]),
                    "lead_time": node.lead_time,
                    "capacity": node.capacity,
                    "total_reward": node.total_reward,
                    "last_order": node.last_order,
                }
                for i, node in enumerate(self.nodes)
            ],
        }

    def is_done(self):
        return self.current_period >= MAX_PERIODS

    def total_rewards(self):
        return [node.total_reward for node in self.nodes]
