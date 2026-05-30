import random

class SupplyChainNode:
    def __init__(self, name, holding_cost_rate, stockout_cost_rate, lead_time):
        self.name = name
        self.inventory = 50
        self.backlog = 0
        self.holding_cost_rate = holding_cost_rate
        self.stockout_cost_rate = stockout_cost_rate
        self.lead_time = lead_time
        
        self.in_transit = []  # List of tuples: (delivery_time, quantity)
        self.total_cost = 0.0
        self.history = []

    def receive_shipments(self, current_time):
        # Add arrived shipments to inventory
        arrived = [q for t, q in self.in_transit if t == current_time]
        self.in_transit = [(t, q) for t, q in self.in_transit if t > current_time]
        total_arrived = sum(arrived)
        self.inventory += total_arrived
        return total_arrived

    def fulfill_demand(self, demand):
        # Total required is new demand + existing backlog
        total_required = demand + self.backlog
        if self.inventory >= total_required:
            fulfilled = total_required
            self.inventory -= total_required
            self.backlog = 0
        else:
            fulfilled = self.inventory
            self.backlog = total_required - self.inventory
            self.inventory = 0
        return fulfilled

    def place_order(self, quantity, current_time):
        delivery_time = current_time + self.lead_time
        self.in_transit.append((delivery_time, quantity))
        return quantity

    def calculate_costs(self):
        cost = (self.inventory * self.holding_cost_rate) + (self.backlog * self.stockout_cost_rate)
        self.total_cost += cost
        return cost

    def step(self, current_time, demand, order_quantity):
        # 1. Receive shipments
        arrived = self.receive_shipments(current_time)
        # 2. Fulfill demand
        fulfilled = self.fulfill_demand(demand)
        # 3. Calculate costs
        step_cost = self.calculate_costs()
        # 4. Place order
        self.place_order(order_quantity, current_time)
        
        state = {
            "time": current_time,
            "inventory": self.inventory,
            "backlog": self.backlog,
            "arrived": arrived,
            "demand": demand,
            "fulfilled": fulfilled,
            "order_quantity": order_quantity,
            "step_cost": step_cost,
            "total_cost": self.total_cost
        }
        self.history.append(state)
        return state

class SupplyChainEnv:
    def __init__(self):
        self.current_time = 0
        # Simple 3 tier: Retailer, Distributor, Supplier
        # For simplicity, demand flows Retailer <- Distributor <- Supplier
        # Supplier is assumed to have infinite inventory to fulfill Distributor
        self.nodes = {
            "Retailer": SupplyChainNode("Retailer", holding_cost_rate=2, stockout_cost_rate=5, lead_time=1),
            "Distributor": SupplyChainNode("Distributor", holding_cost_rate=1, stockout_cost_rate=4, lead_time=2)
        }

    def generate_customer_demand(self):
        # Random demand between 5 and 15
        return random.randint(5, 15)

    def step(self, retailer_order, distributor_order):
        self.current_time += 1
        
        # 1. Generate external demand for retailer
        customer_demand = self.generate_customer_demand()
        
        # 2. Distributor steps: fulfills Retailer's order from LAST time step.
        # Retailer's incoming shipments are managed by Retailer's lead time. 
        # Actually, in a multi-agent system, Retailer's order becomes Distributor's demand.
        distributor_demand = retailer_order
        dist_state = self.nodes["Distributor"].step(self.current_time, distributor_demand, distributor_order)
        
        # 3. Retailer steps:
        # Note: In a real simulation, Retailer only receives what Distributor successfully fulfilled.
        # For this simplified prototype, we assume orders placed are the demand, and we track it.
        # To make it accurate: Retailer's placed order leads to in-transit ONLY if Distributor fulfilled it.
        # We will adjust: Distributor fulfills `dist_fulfilled`. That amount goes to Retailer's in-transit!
        
        # Let's refine Retailer's in-transit logic:
        # We remove the automatic place_order in node.step for Retailer, and inject it from Distributor.
        pass

    # Let's do a refined step
    def step_refined(self, retailer_order, distributor_order):
        self.current_time += 1
        workflow_log = []

        # Customer demand
        customer_demand = self.generate_customer_demand()
        workflow_log.append({"phase": "Demand", "detail": f"Customer demand of {customer_demand} units generated"})

        # --- Distributor Phase ---
        dist_arrived = self.nodes["Distributor"].receive_shipments(self.current_time)
        workflow_log.append({"phase": "Distributor: Receive", "detail": f"{dist_arrived} units arrived from Supplier"})

        dist_fulfilled = self.nodes["Distributor"].fulfill_demand(retailer_order)
        dist_note = "fully fulfilled" if dist_fulfilled >= retailer_order else f"partial — {retailer_order - dist_fulfilled} backordered"
        workflow_log.append({"phase": "Distributor: Fulfill Retailer", "detail": f"Retailer ordered {retailer_order} → {dist_fulfilled} dispatched, {dist_note}"})

        dist_cost = self.nodes["Distributor"].calculate_costs()
        self.nodes["Distributor"].place_order(distributor_order, self.current_time)
        workflow_log.append({"phase": "Distributor: Reorder", "detail": f"Placed order for {distributor_order} units to Supplier (arrives in 2 steps)"})

        # --- Retailer Phase ---
        self.nodes["Retailer"].in_transit.append((self.current_time + self.nodes["Retailer"].lead_time, dist_fulfilled))

        ret_arrived = self.nodes["Retailer"].receive_shipments(self.current_time)
        workflow_log.append({"phase": "Retailer: Receive", "detail": f"{ret_arrived} units arrived from Distributor"})

        ret_fulfilled = self.nodes["Retailer"].fulfill_demand(customer_demand)
        ret_note = "fully fulfilled" if ret_fulfilled >= customer_demand else f"partial — {customer_demand - ret_fulfilled} backordered"
        workflow_log.append({"phase": "Retailer: Fulfill Customer", "detail": f"Customer demand {customer_demand} → {ret_fulfilled} dispatched, {ret_note}"})

        ret_cost = self.nodes["Retailer"].calculate_costs()
        combined = dist_cost + ret_cost
        workflow_log.append({"phase": "Costs", "detail": f"Retailer: ${ret_cost:.2f} | Distributor: ${dist_cost:.2f} | Combined: ${combined:.2f}"})

        # Log state
        self.nodes["Distributor"].history.append({
            "time": self.current_time,
            "inventory": self.nodes["Distributor"].inventory,
            "backlog": self.nodes["Distributor"].backlog,
            "demand": retailer_order,
            "fulfilled": dist_fulfilled,
            "order_placed": distributor_order,
            "cost": dist_cost
        })

        self.nodes["Retailer"].history.append({
            "time": self.current_time,
            "inventory": self.nodes["Retailer"].inventory,
            "backlog": self.nodes["Retailer"].backlog,
            "demand": customer_demand,
            "fulfilled": ret_fulfilled,
            "order_placed": retailer_order,
            "cost": ret_cost
        })

        return {
            "time": self.current_time,
            "customer_demand": customer_demand,
            "retailer": self.nodes["Retailer"].history[-1],
            "distributor": self.nodes["Distributor"].history[-1],
            "workflow_log": workflow_log
        }

    def get_state(self):
        return {
            "time": self.current_time,
            "retailer": {
                "inventory": self.nodes["Retailer"].inventory,
                "backlog": self.nodes["Retailer"].backlog,
                "in_transit": sum([q for t, q in self.nodes["Retailer"].in_transit]),
                "total_cost": self.nodes["Retailer"].total_cost
            },
            "distributor": {
                "inventory": self.nodes["Distributor"].inventory,
                "backlog": self.nodes["Distributor"].backlog,
                "in_transit": sum([q for t, q in self.nodes["Distributor"].in_transit]),
                "total_cost": self.nodes["Distributor"].total_cost
            }
        }
