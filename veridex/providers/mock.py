from __future__ import annotations

import time
import asyncio
from typing import Any, Dict, Optional
from veridex.providers.base import BaseProvider, ProviderResponse


class MockProvider(BaseProvider):
    """
    Mock LLM provider for local testing, benchmarking, and CI/CD verification.
    Supports deterministic rules, simulated latency, token generation, and response overrides.
    """

    def __init__(
        self,
        model: Optional[str] = "mock-model-v1",
        default_response: Optional[str] = None,
        responses: Optional[Dict[str, str]] = None,
        simulated_latency_ms: float = 25.0,
        simulate_success: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self.default_response = default_response or "Mock completion response."
        self.responses = responses or {}
        self.simulated_latency_ms = simulated_latency_ms
        self.simulate_success = simulate_success

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        expected_output: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        start_time = time.perf_counter()

        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        # Match specific response mapping or fall back
        if prompt in self.responses:
            text = self.responses[prompt]
        elif (self.simulate_success or kwargs.get("simulate_success")) and expected_output:
            text = expected_output
        else:
            text = self.default_response

        # If prompt specifies variables or json requests, format appropriately
        if "json" in prompt.lower() and self.default_response == "Mock completion response.":
            text = '{"status": "success", "result": "mock_data"}'

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        prompt_tokens = len(prompt.split())
        completion_tokens = len(text.split())
        total_tokens = prompt_tokens + completion_tokens

        # Estimated mock cost ($0.001 per 1K tokens)
        cost = (total_tokens / 1000.0) * 0.001

        return ProviderResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=round(cost, 6),
            raw_response={"mock": True, "model": self.model},
        )
