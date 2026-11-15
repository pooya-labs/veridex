from __future__ import annotations

import pytest
from veridex.core.models import Assertion, AssertionType
from veridex.integrations.langchain import VeridexCallbackHandler
from veridex.integrations.monitor import GuardrailViolation


class MockLLMResult:
    def __init__(self, text: str, total_tokens: int = 42):
        self.generations = [[MockGeneration(text)]]
        self.llm_output = {"token_usage": {"total_tokens": total_tokens}}


class MockGeneration:
    def __init__(self, text: str):
        self.text = text


def test_langchain_callback_pass():
    handler = VeridexCallbackHandler(
        assertions=[
            Assertion(type=AssertionType.VALID_JSON),
            Assertion(type=AssertionType.NO_PII),
        ]
    )

    handler.on_llm_start({}, ["Extract JSON:"])
    mock_res = MockLLMResult('{"status": "ok", "user": "pooya"}', total_tokens=55)
    handler.on_llm_end(mock_res)

    summary = handler.get_summary()
    assert summary["total_calls"] == 1
    assert summary["passed_calls"] == 1
    assert summary["pass_rate"] == 1.0
    assert summary["total_violations"] == 0
    assert handler.records[0]["total_tokens"] == 55


def test_langchain_callback_violation_recording():
    handler = VeridexCallbackHandler(
        assertions=[
            Assertion(type=AssertionType.NO_PII),
        ],
        raise_on_violation=False,
    )

    handler.on_llm_start({}, ["Give me your email"])
    mock_res = MockLLMResult("Reach out to alice@example.com for help.")
    handler.on_llm_end(mock_res)

    summary = handler.get_summary()
    assert summary["total_calls"] == 1
    assert summary["passed_calls"] == 0
    assert summary["pass_rate"] == 0.0
    assert summary["total_violations"] >= 1
    assert handler.records[0]["passed"] is False


def test_langchain_callback_raise_on_violation():
    handler = VeridexCallbackHandler(
        assertions=[
            Assertion(type=AssertionType.VALID_JSON),
        ],
        raise_on_violation=True,
    )

    handler.on_llm_start({}, ["Output json"])
    mock_res = MockLLMResult("Not a json at all")

    with pytest.raises(GuardrailViolation) as exc_info:
        handler.on_llm_end(mock_res)

    assert "violated Veridex guardrails" in str(exc_info.value)
