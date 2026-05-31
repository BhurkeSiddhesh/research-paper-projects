import json
import re
import random
import requests

from environment import STAGE_NAMES


class LLMAgent:
    def __init__(self, role, provider="mock", api_key=None, base_url=None, model=None):
        self.role = role
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def generate_order_decision(self, node_state):
        if self.provider == "mock":
            return self._mock_decision(node_state)
        prompt = self._build_prompt(node_state)
        if self.provider == "gemini":
            return self._gemini_call(prompt, node_state)
        if self.provider == "ollama":
            return self._ollama_call(prompt, node_state)
        if self.provider == "openrouter":
            return self._openrouter_call(prompt, node_state)
        return self._mock_decision(node_state)

    # ── Prompt (paper Figure 4 / 5 format) ────────────────────────────────

    def _build_prompt(self, s):
        stage_num = s["stage"] + 1
        period    = s.get("period", s.get("time", "?"))
        pipeline  = s.get("pipeline", [])
        arriving  = pipeline[0] if pipeline else 0
        hist      = s.get("sales_history", [])
        avg_sales = round(sum(hist) / len(hist), 1) if hist else 0

        if stage_num == 1:
            demand_line = f"The customer demand in this round is not yet known (you observe {avg_sales:.1f} avg recent sales)."
            downstream_line = "You are the most downstream stage; you face external customer demand directly."
        else:
            downstream_line = (
                f"The downstream stage ({STAGE_NAMES[stage_num - 2]}) has placed an order. "
                f"Your backlog is {s['backlog']} units (unmet downstream demand)."
            )
            demand_line = downstream_line

        strategy = (
            "Minimize total costs: holding cost for excess inventory and backlog cost for unmet demand. "
            "Balance ordering enough to avoid stockouts without over-ordering and accumulating holding costs. "
            "Orders are capped at your capacity."
        )

        return (
            f"Now this is round {period}, stage {stage_num} of 4 ({s['name']}). "
            f"Given your current state:\n"
            f"- Inventory on hand: {s['inventory']} units\n"
            f"- Backlog (unmet demand): {s['backlog']} units\n"
            f"- Upstream backlog (owed to you): {s.get('upstream_backlog', 0)} units\n"
            f"- In-pipeline (arriving next periods): {pipeline}\n"
            f"- Units arriving next period: {arriving}\n"
            f"- Sales history (last periods): {hist}\n"
            f"- Lead time: {s.get('lead_time', 2)} periods | Capacity: {s.get('capacity', 20)} units\n\n"
            f"{demand_line}\n\n"
            f"What is your action for this round?\n"
            f"{strategy}\n\n"
            f"Please state your reason in 1-2 sentences first and then provide your action "
            f"as a non-negative integer within brackets (e.g. [0])."
        )

    # ── Response parsing ───────────────────────────────────────────────────

    def _parse_response(self, text, fallback_state):
        text = text.strip()

        # Primary: paper bracket format [N]
        m = re.search(r'\[(\d+)\]', text)
        if m:
            reasoning = text[:text.rfind('[')].strip() or text
            return {
                "reasoning": reasoning[:500],
                "order_quantity": max(0, int(m.group(1)))
            }

        # Fallback tier 1: standard JSON
        text_clean = re.sub(r"^```(?:json)?\s*", "", text)
        text_clean = re.sub(r"\s*```$", "", text_clean)
        for candidate in [text_clean, re.sub(r'(?<!\\)\n', r'\\n', text_clean)]:
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

        # Fallback tier 2: regex on JSON fields
        order_match     = re.search(r'"order_quantity"\s*:\s*(\d+)', text)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.|\n)*)', text)
        if order_match:
            return {
                "reasoning": (reasoning_match.group(1).replace('\\n', ' ').strip()
                              if reasoning_match else text[:500]),
                "order_quantity": max(0, int(order_match.group(1)))
            }

        # Give up
        mock = self._mock_decision(fallback_state)
        mock["reasoning"] = f"[LLM parse failed — raw: {text[:150]}]"
        return mock

    # ── Providers ──────────────────────────────────────────────────────────

    def _gemini_call(self, prompt, fallback_state):
        model = self.model or "gemini-1.5-flash"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.api_key}"
        )
        gen_config = {"temperature": 0.4, "maxOutputTokens": 1024}
        if "2.5" in model or "2.0" in model:
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config
        }
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            candidate = resp.json()["candidates"][0]
            parts = candidate.get("content", {}).get("parts", [])
            if not parts:
                raise ValueError(f"Empty response (finishReason={candidate.get('finishReason')})")
            text = next(
                (p["text"] for p in parts if not p.get("thought", False) and "text" in p),
                parts[0].get("text", "")
            )
            return self._parse_response(text, fallback_state)
        except Exception as e:
            fallback = self._mock_decision(fallback_state)
            fallback["reasoning"] = f"Gemini error: {e}"
            return fallback

    def _ollama_call(self, prompt, fallback_state):
        base = (self.base_url or "http://localhost:11434").rstrip("/")
        url = f"{base}/api/generate"
        payload = {
            "model": self.model or "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.4}
        }
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            text = resp.json()["response"]
            return self._parse_response(text, fallback_state)
        except Exception as e:
            fallback = self._mock_decision(fallback_state)
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
            fallback = self._mock_decision(fallback_state)
            fallback["reasoning"] = f"OpenRouter error: {e}"
            return fallback

    # ── Mock fallback (base-stock heuristic) ──────────────────────────────

    def _mock_decision(self, s):
        capacity = s.get("capacity", 20)
        inv      = s.get("inventory", 0)
        backlog  = s.get("backlog", 0)
        up_back  = s.get("upstream_backlog", 0)
        pipeline = s.get("pipeline", [])

        position = inv - backlog + up_back + sum(pipeline)
        desired  = capacity
        order    = min(capacity, max(0, desired - position))

        reasoning = (
            f"Inventory position = inv({inv}) - backlog({backlog}) + upstream_backlog({up_back}) "
            f"+ pipeline({sum(pipeline)}) = {position}. "
            f"Target = capacity ({desired}). "
            f"Ordering {order} units. [{order}]"
        )
        return {"reasoning": reasoning, "order_quantity": order}
