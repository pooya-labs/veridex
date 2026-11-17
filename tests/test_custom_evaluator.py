from __future__ import annotations

import pytest
from veridex import Assertion, AssertionType, EvaluatorRegistry, register_evaluator, guard


def test_custom_evaluator_function_registration():
    @register_evaluator("polite_tone")
    def check_polite(output: str, **kwargs) -> bool:
        return "please" in output.lower() or "thank you" in output.lower()

    registry = EvaluatorRegistry()
    assertion = Assertion(type="polite_tone")

    res_pass = registry.evaluate(assertion, "Thank you for reaching out to support.")
    assert res_pass.passed is True
    assert res_pass.score == 1.0

    res_fail = registry.evaluate(assertion, "Give me your account number immediately.")
    assert res_fail.passed is False
    assert res_fail.score == 0.0


def test_custom_evaluator_with_guardrail():
    @register_evaluator("no_forbidden_word")
    def forbid_secret(output: str, **kwargs) -> bool:
        return "classified_omega" not in output

    # Should pass
    out1 = guard("This is public information.", assertions=[{"type": "no_forbidden_word"}])
    assert out1 == "This is public information."

    # Should trigger fallback
    out2 = guard(
        "Here is the classified_omega document.",
        assertions=[{"type": "no_forbidden_word"}],
        fallback="REDACTED",
    )
    assert out2 == "REDACTED"
