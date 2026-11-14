from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from veridex.core.models import Assertion, AssertionType, TestCase, TestResult
from veridex.evaluators import EvaluatorRegistry


def assert_eval(
    output: str,
    assertions: List[Union[Dict[str, Any], str, Assertion]],
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Convenient programmatic assertion helper for pytest and CI tests.
    Raises AssertionError if any assertion fails with clear diagnostic details.

    Example:
        assert_eval(
            output='{"status": "success", "ticket": "TCK-102"}',
            assertions=[
                {"type": "valid_json"},
                {"type": "contains", "value": "TCK-"}
            ]
        )
    """
    registry = EvaluatorRegistry()
    parsed_assertions: list[Assertion] = []

    for a in assertions:
        if isinstance(a, str):
            parsed_assertions.append(Assertion(type=AssertionType(a)))
        elif isinstance(a, dict):
            parsed_assertions.append(Assertion.model_validate(a))
        elif isinstance(a, Assertion):
            parsed_assertions.append(a)

    failures: list[str] = []
    for assertion in parsed_assertions:
        res = registry.evaluate(assertion, output, context=context)
        if not res.passed:
            failures.append(f"[{res.assertion_type}] {res.message}")

    if failures:
        msg = f"Veridex assertion(s) failed on output:\nOutput: {repr(output[:120])}\nViolations:\n" + "\n".join(f"  ✗ {f}" for f in failures)
        raise AssertionError(msg)
