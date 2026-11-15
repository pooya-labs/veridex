from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from veridex.core.models import Assertion
from veridex.integrations.monitor import GuardrailViolation, guard, _parse_assertions

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Fallback callback handler protocol when langchain is not installed."""
        pass


class VeridexCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that monitors LLM completions, runs
    automated Veridex assertions/guardrails, and records latencies & tokens.
    """

    def __init__(
        self,
        assertions: Optional[List[Assertion]] = None,
        raise_on_violation: bool = False,
        fallback_value: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.assertions = assertions or []
        self.raise_on_violation = raise_on_violation
        self.fallback_value = fallback_value
        self.records: List[Dict[str, Any]] = []
        self._start_times: Dict[str, float] = {}
        self._prompts: Dict[str, List[str]] = {}

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        key = str(run_id) if run_id else f"run_{len(self.records)}"
        self._start_times[key] = time.perf_counter()
        self._prompts[key] = prompts

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Optional[UUID] = None,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        key = str(run_id) if run_id else f"run_{len(self.records)}"
        duration_ms = (time.perf_counter() - self._start_times.pop(key, time.perf_counter())) * 1000.0
        prompts = self._prompts.pop(key, [])

        # Extract text completions from LangChain LLMResult
        generations = getattr(response, "generations", [])
        completion_texts: List[str] = []
        for gen_list in generations:
            for gen in gen_list:
                text = getattr(gen, "text", "") or getattr(getattr(gen, "message", None), "content", "")
                if text:
                    completion_texts.append(str(text))

        # Token usage if present in llm_output
        llm_output = getattr(response, "llm_output", {}) or {}
        token_usage = llm_output.get("token_usage", {}) or {}
        total_tokens = token_usage.get("total_tokens", 0)

        # Run guardrails/assertions if configured
        passed = True
        violation_messages: List[str] = []

        if self.assertions and completion_texts:
            for idx, text in enumerate(completion_texts):
                p = prompts[idx] if idx < len(prompts) else None
                try:
                    guard(output=text, assertions=self.assertions, prompt=p)
                except GuardrailViolation as gv:
                    passed = False
                    violation_messages.extend(gv.violations)

        record = {
            "run_id": key,
            "duration_ms": round(duration_ms, 2),
            "total_tokens": total_tokens,
            "prompts": prompts,
            "completions": completion_texts,
            "passed": passed,
            "violations": violation_messages,
        }
        self.records.append(record)

        if not passed and self.raise_on_violation:
            snippet = completion_texts[0][:100] if completion_texts else ""
            raise GuardrailViolation(
                f"LangChain LLM completion violated Veridex guardrails: {'; '.join(violation_messages)}",
                violations=violation_messages,
                output_snippet=snippet,
            )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        key = str(run_id) if run_id else f"run_{len(self.records)}"
        self._start_times.pop(key, None)
        self._prompts.pop(key, None)
        self.records.append({
            "run_id": key,
            "error": str(error),
            "passed": False,
            "violations": [str(error)],
        })

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.records)
        if total == 0:
            return {"total_calls": 0, "pass_rate": 1.0, "avg_latency_ms": 0.0, "total_violations": 0}

        passed = sum(1 for r in self.records if r.get("passed", False))
        violations = sum(len(r.get("violations", [])) for r in self.records)
        durations = [r.get("duration_ms", 0.0) for r in self.records if "duration_ms" in r]
        avg_lat = sum(durations) / len(durations) if durations else 0.0

        return {
            "total_calls": total,
            "passed_calls": passed,
            "failed_calls": total - passed,
            "pass_rate": round(passed / total, 4),
            "avg_latency_ms": round(avg_lat, 2),
            "total_violations": violations,
        }
