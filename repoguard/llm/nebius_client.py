"""Nebius AI Studio LLM Client for Llama-3-Nemotron-70B-Instruct."""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from openai import OpenAI

from ..config import settings

logger = logging.getLogger("repoguard.nebius")


class NebiusClient:
    """Interface to Nebius AI Studio Token API using OpenAI-compatible client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.nebius_api_key
        self.base_url = base_url or settings.nebius_base_url
        self.model = model or settings.nebius_model
        self.is_mock = not bool(self.api_key and not self.api_key.startswith("your-"))

        if not self.is_mock:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
            logger.info("Connected to Nebius AI Studio (%s) using model: %s", self.base_url, self.model)
        else:
            self.client = None
            logger.warning(
                "No NEBIUS_API_KEY detected. Running in simulated Nemotron-70B inference mode for demo & testing."
            )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2500,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute chat completion using Nebius endpoint or deterministic mock fallback."""
        if not self.is_mock and self.client:
            start_t = time.perf_counter()
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format

            try:
                response = self.client.chat.completions.create(**kwargs)
                latency = time.perf_counter() - start_t
                content = response.choices[0].message.content or ""
                logger.info(
                    "Nebius Nemotron completion succeeded in %.2fs (Tokens: prompt=%d, completion=%d)",
                    latency,
                    response.usage.prompt_tokens if response.usage else 0,
                    response.usage.completion_tokens if response.usage else 0,
                )
                return content
            except Exception as e:
                logger.error("Error communicating with Nebius API: %s. Falling back to simulated reasoning.", e)
                return self._simulate_nemotron_reasoning(messages)

        return self._simulate_nemotron_reasoning(messages)

    def _simulate_nemotron_reasoning(self, messages: List[Dict[str, str]]) -> str:
        """Simulate realistic Llama-3-Nemotron-70B-Instruct reasoning for offline demo and CI reproduction."""
        time.sleep(0.5)  # simulate fast GPU inference latency
        
        sys_msg = messages[0].get("content", "") if messages else ""
        user_msg = messages[1].get("content", "") if len(messages) > 1 else ""

        # Phase 1: REFLECTION
        if "Self-Correction" in sys_msg or "REFLECTION" in sys_msg:
            return json.dumps({
                "prior_flaw": "The previous patch raised ValueError on empty input instead of returning 0.0, breaking edge-case assertions.",
                "new_hypothesis": "The function must return 0.0 when input prices list is empty or when all filtered prices are negative.",
                "adjustments_required": "Return 0.0 on empty or all-filtered prices, and ensure division is guarded."
            }, indent=2)

        # Phase 2: PATCH
        if "Patch Synthesis Engine" in sys_msg or "PATCH" in sys_msg:
            # If reflection feedback is present, synthesize the corrected patch!
            if "Attempt 1" in user_msg or "Attempt" in user_msg or "flaw" in user_msg.lower():
                return json.dumps({
                    "explanation": "Safely handle empty lists and negative price filtering without division by zero.",
                    "target_file": "math_lib.py",
                    "fixed_code": (
                        '"""Sample business logic library containing an intentional edge-case bug for CI/CD healing demo."""\n\n'
                        'def calculate_discounted_average(prices: list[float], discount: float = 0.0) -> float:\n'
                        '    """Calculate average price after applying discount factor (0.0 to 1.0).\n'
                        '    \n'
                        '    Filters out invalid negative price values.\n'
                        '    """\n'
                        '    if not prices:\n'
                        '        return 0.0\n'
                        '    valid_prices = [p for p in prices if p >= 0]\n'
                        '    if not valid_prices:\n'
                        '        return 0.0\n'
                        '    total = sum(valid_prices) * (1.0 - discount)\n'
                        '    return round(total / len(valid_prices), 2)\n\n\n'
                        'def compute_tax(subtotal: float, rate: float = 0.08) -> float:\n'
                        '    """Compute sales tax amount."""\n'
                        '    if subtotal < 0:\n'
                        '        return 0.0\n'
                        '    return round(subtotal * rate, 2)\n'
                    )
                }, indent=2)
            else:
                # First patch attempt: introduces a regression on empty list to trigger the self-correction reflection loop
                return json.dumps({
                    "explanation": "Added zero check for valid_prices division.",
                    "target_file": "math_lib.py",
                    "fixed_code": (
                        '"""Sample business logic library containing an intentional edge-case bug for CI/CD healing demo."""\n\n'
                        'def calculate_discounted_average(prices: list[float], discount: float = 0.0) -> float:\n'
                        '    """Calculate average price after applying discount factor (0.0 to 1.0).\n'
                        '    \n'
                        '    Filters out invalid negative price values.\n'
                        '    """\n'
                        '    valid_prices = [p for p in prices if p > 0]\n'
                        '    if not valid_prices:\n'
                        '        raise ValueError("No valid prices found")\n'
                        '    total = sum(valid_prices) * (1.0 - discount)\n'
                        '    return round(total / len(valid_prices), 2)\n\n\n'
                        'def compute_tax(subtotal: float, rate: float = 0.08) -> float:\n'
                        '    """Compute sales tax amount."""\n'
                        '    if subtotal < 0:\n'
                        '        return 0.0\n'
                        '    return round(subtotal * rate, 2)\n'
                    )
                }, indent=2)

        # Phase 3: DIAGNOSTIC
        if "Attempt 1" in user_msg or "flaw" in user_msg.lower():
            return json.dumps({
                "root_cause": "The initial patch addressed zero division but raised ValueError on empty inputs instead of returning 0.0.",
                "bug_type": "EdgeCaseRegression",
                "target_file": "math_lib.py",
                "failing_symbol": "calculate_discounted_average",
                "reflection_analysis": "The previous patch was overly aggressive by raising ValueError. The specification requires returning 0.0 for empty collections.",
                "recommended_action": "Check `if not prices:` and return 0.0 directly, and return 0.0 if all filtered prices are negative."
            }, indent=2)
        else:
            return json.dumps({
                "root_cause": "ZeroDivisionError in calculate_discounted_average: len(valid_prices) is 0 when prices is empty or negative.",
                "bug_type": "ZeroDivisionError",
                "target_file": "math_lib.py",
                "failing_symbol": "calculate_discounted_average",
                "reflection_analysis": "Direct division total / len(valid_prices) without guarding for len == 0 causes unhandled crash on empty price lists.",
                "recommended_action": "Validate price list length before division and handle empty collections gracefully."
            }, indent=2)
        return json.dumps({
            "status": "success",
            "message": "Nebius Llama-3-Nemotron-70B analyzed the context."
        })


_client_instance: Optional[NebiusClient] = None

def get_nebius_client() -> NebiusClient:
    """Retrieve or initialize singleton NebiusClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = NebiusClient()
    return _client_instance
