from environment import LMAX


class BaseStockPolicy:
    """
    Desired inventory position = capacity.
    Order = min(capacity, max(0, desired - inv - upstream_backlog - sum(pipeline)))
    """
    def decide(self, node_state):
        desired = node_state["capacity"]
        position = (
            node_state["inventory"]
            - node_state["backlog"]
            + node_state["upstream_backlog"]
            + sum(node_state["pipeline"])
        )
        order = min(node_state["capacity"], max(0, desired - position))
        return int(order)


class TrackingDemandPolicy:
    """
    Desired inventory position = avg_sales(last LMAX periods) * lead_time + backlog.
    Order = min(capacity, max(0, desired - inv - upstream_backlog - sum(pipeline)))
    """
    def decide(self, node_state):
        hist = node_state["sales_history"]
        avg_sales = (sum(hist) / len(hist)) if hist else 0
        desired = avg_sales * node_state["lead_time"] + node_state["backlog"]
        position = (
            node_state["inventory"]
            - node_state["backlog"]
            + node_state["upstream_backlog"]
            + sum(node_state["pipeline"])
        )
        order = min(node_state["capacity"], max(0, desired - position))
        return int(order)


def run_baseline_episode(env_class, scenario_name, policy_class):
    """Run a complete 12-period episode using the given policy. Returns total rewards per stage."""
    from environment import SupplyChainEnv
    env = SupplyChainEnv(scenario_name)
    policy = policy_class()
    while not env.is_done():
        state = env.get_state()
        actions = [policy.decide(s) for s in state["stages"]]
        env.step(actions)
    return env.total_rewards()
