from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional
import httpx
from veridex.providers.base import BaseProvider, ProviderResponse


class HttpEndpointProvider(BaseProvider):
    """
    Provider that sends evaluation prompts to an arbitrary live HTTP REST endpoint.
    Ideal for evaluating custom deployed RAG pipelines, FastAPI services, and AI agents.
    """

    def __init__(
        self,
        endpoint_url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        payload_template: Optional[Dict[str, Any]] = None,
        response_path: Optional[str] = None,
        timeout_seconds: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model="http-endpoint", **kwargs)
        self.endpoint_url = endpoint_url
        self.method = method.upper()
        self.headers = headers or {"Content-Type": "application/json"}
        self.payload_template = payload_template or {"prompt": "{{ prompt }}"}
        self.response_path = response_path
        self.timeout_seconds = timeout_seconds

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ProviderResponse:
        start_time = time.perf_counter()

        # Render payload template
        payload = self._render_template(self.payload_template, prompt, system_prompt)

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            if self.method == "POST":
                resp = await client.post(self.endpoint_url, headers=self.headers, json=payload)
            elif self.method == "GET":
                resp = await client.get(self.endpoint_url, headers=self.headers, params=payload)
            else:
                resp = await client.request(self.method, self.endpoint_url, headers=self.headers, json=payload)

            resp.raise_for_status()
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            # Parse response
            raw_data: Any
            try:
                raw_data = resp.json()
                text = self._extract_response_text(raw_data, self.response_path)
            except Exception:
                text = resp.text
                raw_data = {"raw_text": resp.text}

        tokens = len(prompt.split()) + len(text.split())

        return ProviderResponse(
            text=text,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            total_tokens=tokens,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=0.0,
            raw_response=raw_data if isinstance(raw_data, dict) else {"result": raw_data},
        )

    @classmethod
    def _render_template(cls, template: Any, prompt: str, system_prompt: Optional[str]) -> Any:
        if isinstance(template, dict):
            return {k: cls._render_template(v, prompt, system_prompt) for k, v in template.items()}
        elif isinstance(template, list):
            return [cls._render_template(item, prompt, system_prompt) for item in template]
        elif isinstance(template, str):
            rendered = template.replace("{{ prompt }}", prompt).replace("{{prompt}}", prompt)
            if system_prompt:
                rendered = rendered.replace("{{ system_prompt }}", system_prompt).replace("{{system_prompt}}", system_prompt)
            return rendered
        return template

    @staticmethod
    def _extract_response_text(data: Any, path: Optional[str]) -> str:
        if not path:
            # Common default field fallbacks
            if isinstance(data, dict):
                for candidate in ["text", "response", "output", "answer", "result", "content"]:
                    if candidate in data:
                        return str(data[candidate])
            return json.dumps(data) if not isinstance(data, str) else data

        tokens = path.split(".")
        curr = data
        for t in tokens:
            if isinstance(curr, dict) and t in curr:
                curr = curr[t]
            else:
                return str(data)
        return str(curr)
