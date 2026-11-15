from __future__ import annotations

import pytest
from veridex.integrations.monitor import GuardrailViolation, guard, async_guard, monitor


def test_guard_pass_and_fail():
    # Pass
    safe_output = '{"status": "ok", "user": "John"}'
    res = guard(
        output=safe_output,
        assertions=[
            {"type": "valid_json"},
            {"type": "no_pii"},
        ],
    )
    assert res == safe_output

    # Fail without fallback -> raises GuardrailViolation
    leaked_output = "Secret key: sk-proj992182019284719284"
    with pytest.raises(GuardrailViolation) as exc_info:
        guard(
            output=leaked_output,
            assertions=["no_pii"],
        )
    assert "no_pii" in str(exc_info.value)
    assert len(exc_info.value.violations) >= 1

    # Fail with fallback -> returns fallback
    fallback_res = guard(
        output=leaked_output,
        assertions=["no_pii"],
        fallback="Blocked: PII Violation",
    )
    assert fallback_res == "Blocked: PII Violation"


def test_async_guard():
    import asyncio
    async def _run():
        valid = "Hello world!"
        res = await async_guard(valid, assertions=[{"type": "contains", "value": "world"}])
        assert res == valid

        with pytest.raises(GuardrailViolation):
            await async_guard("System prompt override enabled", assertions=["no_jailbreak"])

    asyncio.run(_run())


def test_monitor_decorator_sync():
    @monitor(assertions=["valid_json"], fallback='{"error": "invalid"}')
    def generate_json(prompt: str) -> str:
        if "bad" in prompt:
            return "This is not json"
        return '{"result": 42}'

    assert generate_json("good prompt") == '{"result": 42}'
    assert generate_json("bad prompt") == '{"error": "invalid"}'


def test_monitor_decorator_async():
    import asyncio
    async def _run():
        @monitor(assertions=["no_pii"])
        async def chat_agent(prompt: str) -> str:
            if "leak" in prompt:
                return "Customer email: admin@secret.internal"
            return "Clean response"

        clean = await chat_agent("hello")
        assert clean == "Clean response"

        with pytest.raises(GuardrailViolation):
            await chat_agent("leak")

    asyncio.run(_run())
