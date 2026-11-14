from __future__ import annotations

from typing import Any, Dict, Optional
from veridex.providers.base import BaseProvider, ProviderResponse
from veridex.providers.mock import MockProvider
from veridex.providers.openai_provider import OpenAIProvider
from veridex.providers.gemini_provider import GeminiProvider
from veridex.providers.http_provider import HttpEndpointProvider


def get_provider(
    provider_name: str,
    model: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    **kwargs: Any,
) -> BaseProvider:
    """Factory function to instantiate an LLM provider."""
    name = (provider_name or "mock").lower()

    if name in {"mock", "dummy", "fake"}:
        return MockProvider(model=model, **kwargs)
    elif name in {"openai", "ollama", "vllm", "openrouter", "groq"}:
        return OpenAIProvider(model=model, **kwargs)
    elif name in {"gemini", "google"}:
        return GeminiProvider(model=model, **kwargs)
    elif name in {"http", "rest", "webhook", "api", "endpoint"}:
        target_url = endpoint_url or kwargs.get("url")
        if not target_url:
            raise ValueError("Endpoint URL must be specified when using HTTP provider.")
        return HttpEndpointProvider(endpoint_url=target_url, **kwargs)

    raise ValueError(f"Unsupported provider: '{provider_name}'. Supported: mock, openai, gemini, http.")


__all__ = [
    "BaseProvider",
    "ProviderResponse",
    "MockProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "HttpEndpointProvider",
    "get_provider",
]
