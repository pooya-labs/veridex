from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Union
from veridex.core.models import Assertion, AssertionType
from veridex.evaluators import EvaluatorRegistry


class GuardrailViolation(Exception):
    """
    Raised when an LLM completion violates one or more Veridex guardrails.
    Contains detailed diagnostics of each violated assertion.
    """

    def __init__(self, message: str, violations: List[str], output_snippet: str):
        super().__init__(message)
        self.violations = violations
        self.output_snippet = output_snippet


def _parse_assertions(raw_assertions: List[Union[Dict[str, Any], str, Assertion]]) -> List[Assertion]:
    parsed: List[Assertion] = []
    for a in raw_assertions:
        if isinstance(a, str):
            parsed.append(Assertion(type=AssertionType(a)))
        elif isinstance(a, dict):
            parsed.append(Assertion.model_validate(a))
        elif isinstance(a, Assertion):
            parsed.append(a)
    return parsed


def guard(
    output: str,
    assertions: List[Union[Dict[str, Any], str, Assertion]],
    prompt: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    fallback: Optional[str] = None,
) -> str:
    """
    Synchronously validates an LLM completion against Veridex assertions in production.
    If all assertions pass, returns the original output.
    If any assertion fails:
      - If fallback is provided, returns fallback string.
      - Otherwise, raises GuardrailViolation with diagnostic reasons.

    Example:
        clean_text = guard(
            output=model_response,
            assertions=[
                {"type": "no_pii"},
                {"type": "no_jailbreak"},
                {"type": "valid_json"},
            ],
            fallback='{"error": "Safety violation"}'
        )
    """
    registry = EvaluatorRegistry()
    parsed = _parse_assertions(assertions)

    eval_context = context.copy() if context else {}
    if prompt:
        eval_context["prompt"] = prompt

    failures: List[str] = []
    for assertion in parsed:
        res = registry.evaluate(assertion, output, context=eval_context)
        if not res.passed:
            failures.append(f"[{res.assertion_type}] {res.message}")

    if failures:
        if fallback is not None:
            return fallback
        snippet = output[:100] + "..." if len(output) > 100 else output
        raise GuardrailViolation(
            message=f"Veridex Guardrail Violation: {len(failures)} assertion(s) failed.\n" + "\n".join(f"  ✗ {f}" for f in failures),
            violations=failures,
            output_snippet=snippet,
        )

    return output


async def async_guard(
    output: str,
    assertions: List[Union[Dict[str, Any], str, Assertion]],
    prompt: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    fallback: Optional[str] = None,
) -> str:
    """Asynchronous variant of guard."""
    return guard(output, assertions, prompt=prompt, context=context, fallback=fallback)


def monitor(
    assertions: List[Union[Dict[str, Any], str, Assertion]],
    fallback: Optional[str] = None,
    prompt_arg_name: Optional[str] = "prompt",
) -> Callable:
    """
    Decorator for LLM client or agent functions. Automatically intercepts returned
    completions (sync or async) and applies Veridex guardrails.

    Example:
        @monitor(assertions=["no_pii", "no_jailbreak"])
        def call_my_agent(prompt: str) -> str:
            return client.chat(prompt)
    """
    def decorator(fn: Callable) -> Callable:
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                prompt_val = kwargs.get(prompt_arg_name) if prompt_arg_name else None
                if not prompt_val and args and isinstance(args[0], str):
                    prompt_val = args[0]

                res = await fn(*args, **kwargs)
                if isinstance(res, str):
                    return await async_guard(res, assertions, prompt=prompt_val, fallback=fallback)
                return res
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                prompt_val = kwargs.get(prompt_arg_name) if prompt_arg_name else None
                if not prompt_val and args and isinstance(args[0], str):
                    prompt_val = args[0]

                res = fn(*args, **kwargs)
                if isinstance(res, str):
                    return guard(res, assertions, prompt=prompt_val, fallback=fallback)
                return res
            return sync_wrapper

    return decorator
