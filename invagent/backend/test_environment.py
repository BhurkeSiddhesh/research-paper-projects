import unittest
from environment import SupplyChainEnv, SupplyChainNode

class TestSupplyChainEnv(unittest.TestCase):
    def test_node_inventory_logic(self):
        node = SupplyChainNode("Test", 1, 2, lead_time=1)
        self.assertEqual(node.inventory, 50)
        self.assertEqual(node.backlog, 0)
        
        # Test fulfilling demand within inventory
        fulfilled = node.fulfill_demand(10)
        self.assertEqual(fulfilled, 10)
        self.assertEqual(node.inventory, 40)
        
        # Test fulfilling demand exceeding inventory
        fulfilled = node.fulfill_demand(50)
        self.assertEqual(fulfilled, 40)
        self.assertEqual(node.inventory, 0)
        self.assertEqual(node.backlog, 10)
        
        # Test receiving shipments
        node.in_transit.append((1, 20)) # Delivery at time 1
        arrived = node.receive_shipments(1)
        self.assertEqual(arrived, 20)
        self.assertEqual(node.inventory, 20)
        
        # Fulfill backlog
        fulfilled = node.fulfill_demand(0) # No new demand, just backlog
        self.assertEqual(fulfilled, 10)
        self.assertEqual(node.inventory, 10)
        self.assertEqual(node.backlog, 0)

    def test_env_step(self):
        env = SupplyChainEnv()
        initial_state = env.get_state()
        self.assertEqual(initial_state["retailer"]["inventory"], 50)
        
        # Step simulation
        res = env.step_refined(retailer_order=15, distributor_order=20)
        self.assertIn("retailer", res)
        self.assertIn("distributor", res)

if __name__ == '__main__':
    unittest.main()
