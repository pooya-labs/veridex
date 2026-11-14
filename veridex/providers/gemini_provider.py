from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
import httpx
from veridex.providers.base import BaseProvider, ProviderResponse


class GeminiProvider(BaseProvider):
    """
    Provider for Google Gemini API via REST endpoints.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model or "gemini-1.5-flash", **kwargs)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ProviderResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        contents = [{"parts": [{"text": prompt}]}]
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_prompt:
            body["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

        latency_ms = (time.perf_counter() - start) * 1000.0

        candidates = data.get("candidates", [])
        text = ""
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                text = parts[0].get("text", "")

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)

        cost = (prompt_tokens * 0.075 + completion_tokens * 0.30) / 1_000_000.0

        return ProviderResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=round(cost, 6),
            raw_response=data,
        )
