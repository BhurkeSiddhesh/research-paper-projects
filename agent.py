import json
import re
import random
import requests


class LLMAgent:
    def __init__(self, role, provider="mock", api_key=None, base_url=None, model=None):
        self.role = role
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def generate_order_decision(self, state):
        if self.provider == "mock":
            return self._mock_llm_call(state)
        prompt = self._build_prompt(state)
        if self.provider == "gemini":
            return self._gemini_call(prompt, state)
        if self.provider == "ollama":
            return self._ollama_call(prompt, state)
        if self.provider == "openrouter":
            return self._openrouter_call(prompt, state)
        return self._mock_llm_call(state)

    def _build_prompt(self, state):
        cost_line = (
            "Holding cost $2/unit/period, Stockout cost $5/unit/period"
            if self.role == "Retailer"
            else "Holding cost $1/unit/period, Stockout cost $4/unit/period"
        )
        return (
            f"You are an autonomous supply chain agent acting as the {self.role} "
            f"in a Beer Game simulation.\n"
            f"Goal: minimise total costs (holding + stockout) while meeting demand.\n\n"
            f"Current state (time step {state.get('time', '?')}):\n"
            f"- Inventory on hand  : {state['inventory']} units\n"
            f"- Backlog (unmet)    : {state['backlog']} units\n"
            f"- In-transit orders  : {state['in_transit']} units\n"
            f"- Cost structure     : {cost_line}\n\n"
            f"Decide how many units to order from your upstream supplier this period.\n\n"
            f"IMPORTANT: reply with ONLY a single-line JSON object. "
            f"Put all reasoning on ONE line (use '; ' not newlines to separate steps). "
            f"No markdown, no extra text:\n"
            f'{{ "reasoning": "step1; step2; step3", "order_quantity": 5 }}'
        )

    def _parse_response(self, text, fallback_state):
        text = text.strip()
        # Strip markdown code fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        # Tier 1: standard JSON parse, then with newlines escaped
        for candidate in [text, re.sub(r'(?<!\\)\n', r'\\n', text)]:
            try:
                data = json.loads(candidate)
                return {
                    "reasoning": str(data.get("reasoning", candidate[:500])),
                    "order_quantity": max(0, int(data.get("order_quantity", 0)))
                }
            except Exception:
                pass
            match = re.search(r'\{.*\}', candidate, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                    return {
                        "reasoning": str(data.get("reasoning", candidate[:500])),
                        "order_quantity": max(0, int(data.get("order_quantity", 0)))
                    }
                except Exception:
                    pass

        # Tier 2: regex extraction — works even on structurally broken JSON
        order_match    = re.search(r'"order_quantity"\s*:\s*(\d+)', text)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.|\n)*)', text)
        if order_match:
            return {
                "reasoning": (reasoning_match.group(1).replace('\\n', ' ').strip()
                              if reasoning_match else text[:500]),
                "order_quantity": max(0, int(order_match.group(1)))
            }

        # Tier 3: give up, run mock and tag it
        mock = self._mock_llm_call(fallback_state)
        mock["reasoning"] = f"[LLM parse failed — raw: {text[:150]}]"
        return mock

    # ── Providers ──────────────────────────────────────────────────────────

    def _gemini_call(self, prompt, fallback_state):
        model = self.model or "gemini-1.5-flash"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1024,
                # Force valid JSON output — works for all Gemini models including 2.5
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "reasoning":      {"type": "STRING"},
                        "order_quantity": {"type": "INTEGER"}
                    },
                    "required": ["reasoning", "order_quantity"]
                }
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            parts = resp.json()["candidates"][0]["content"]["parts"]
            # Thinking models (e.g. gemini-2.5-flash) return a thought part first;
            # skip it and take only the non-thought text part.
            text = next(
                (p["text"] for p in parts if not p.get("thought", False)),
                parts[0]["text"]
            )
            return self._parse_response(text, fallback_state)
        except Exception as e:
            fallback = self._mock_llm_call(fallback_state)
            fallback["reasoning"] = f"Gemini error: {e}"
            return fallback

    def _ollama_call(self, prompt, fallback_state):
        base = (self.base_url or "http://localhost:11434").rstrip("/")
        url = f"{base}/api/generate"
        payload = {
            "model": self.model or "llama3",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.4}
        }
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            text = resp.json()["response"]
            return self._parse_response(text, fallback_state)
        except Exception as e:
            fallback = self._mock_llm_call(fallback_state)
            fallback["reasoning"] = f"Ollama error: {e}"
            return fallback

    def _openrouter_call(self, prompt, fallback_state):
        base = (self.base_url or "https://openrouter.ai/api/v1").rstrip("/")
        url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://research-paper-projects.onrender.com",
            "X-Title": "InvAgent Supply Chain Simulation"
        }
        payload = {
            "model": self.model or "openai/gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 512
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(text, fallback_state)
        except Exception as e:
            fallback = self._mock_llm_call(fallback_state)
            fallback["reasoning"] = f"OpenRouter error: {e}"
            return fallback

    # ── Mock fallback ──────────────────────────────────────────────────────

    def _mock_llm_call(self, state):
        position = state["inventory"] + state["in_transit"] - state["backlog"]
        target = 30
        if position < target:
            order_qty = target - position
            reasoning = (
                f"Inventory position: {position} "
                f"(on-hand {state['inventory']} + in-transit {state['in_transit']} "
                f"- backlog {state['backlog']}). "
                f"Target is {target}. Ordering {order_qty} units to close the gap."
            )
        else:
            order_qty = 0
            reasoning = (
                f"Inventory position: {position}, above the target of {target}. "
                f"No order needed this period."
            )
        if random.random() > 0.8 and order_qty > 0:
            adj = random.randint(-2, 5)
            order_qty = max(0, order_qty + adj)
            reasoning += f" Adjusting by {adj:+d} units for anticipated demand variance."
        return {"reasoning": reasoning, "order_quantity": order_qty}
