import os
import json
import random

class LLMAgent:
    def __init__(self, role, use_mock=True):
        self.role = role
        self.use_mock = use_mock
        # We could initialize an OpenAI/Gemini client here if use_mock is False

    def generate_order_decision(self, state):
        """
        Takes the current state of the supply chain node and returns an order quantity and reasoning.
        """
        prompt = self._build_prompt(state)
        
        if self.use_mock:
            return self._mock_llm_call(state)
        else:
            # Here you would call the actual LLM API
            # For example: response = openai.ChatCompletion.create(...)
            # return self._parse_llm_response(response)
            return self._mock_llm_call(state)

    def _build_prompt(self, state):
        return f"""
        You are an autonomous supply chain agent acting as the {self.role}.
        Your goal is to minimize total costs (holding cost + stockout cost) while meeting demand.
        
        Current State:
        - Time: {state['time']}
        - Current Inventory: {state['inventory']}
        - Current Backlog: {state['backlog']}
        - In-Transit Inventory: {state['in_transit']}
        
        Using Chain-of-Thought reasoning, determine how much inventory you should order from your upstream supplier.
        Output your response in JSON format:
        {{
            "reasoning": "Step-by-step logic here...",
            "order_quantity": integer
        }}
        """

    def _mock_llm_call(self, state):
        # A simple heuristic to mock the LLM's CoT
        # Target inventory level = 30
        current_position = state["inventory"] + state["in_transit"] - state["backlog"]
        target = 30
        
        if current_position < target:
            order_qty = target - current_position
            reasoning = f"My current position is {current_position}. I need to reach my target of {target}. I will order {order_qty}."
        else:
            order_qty = 0
            reasoning = f"My current position is {current_position}, which is above the target {target}. I do not need to order."
            
        # Add some randomness to simulate LLM variance
        if random.random() > 0.8 and order_qty > 0:
            order_qty += random.randint(-2, 5)
            reasoning += f" However, I'm adjusting by a bit due to anticipated demand fluctuations."
            
        return {
            "reasoning": reasoning,
            "order_quantity": max(0, order_qty)
        }
