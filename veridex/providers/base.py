from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    """Normalized response from an LLM provider."""
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: Optional[str] = None, **kwargs: Any) -> None:
        self.model = model or "default"
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Asynchronously call the provider to generate a completion."""
        pass
