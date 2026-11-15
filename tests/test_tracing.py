from __future__ import annotations

import json
from pathlib import Path
import pytest
from veridex.integrations.tracing import VeridexTracer, VeridexSpan


def test_tracer_context_manager():
    tracer = VeridexTracer(service_name="payment-service")

    with tracer.trace("llm_fraud_check", model="gpt-4o", provider="openai", prompt="Analyze transaction") as span:
        span.set_attribute("transaction.amount", 250.0)
        span.add_event("token_computed", {"tokens": 48})

    assert len(tracer.spans) == 1
    s = tracer.spans[0]
    assert s.name == "llm_fraud_check"
    assert s.status == "OK"
    assert s.duration_ms >= 0.0
    assert s.attributes["gen_ai.request.model"] == "gpt-4o"
    assert s.attributes["transaction.amount"] == 250.0
    assert len(s.events) == 1


def test_tracer_exception_handling():
    tracer = VeridexTracer()

    with pytest.raises(ValueError):
        with tracer.trace("faulty_eval", model="gemini-1.5-pro") as span:
            raise ValueError("Rate limit exceeded")

    assert len(tracer.spans) == 1
    s = tracer.spans[0]
    assert s.status == "ERROR"
    assert s.events[0]["name"] == "exception"
    assert s.events[0]["attributes"]["exception.type"] == "ValueError"


def test_tracer_export_jsonl(tmp_path: Path):
    tracer = VeridexTracer(service_name="test-service")
    span = tracer.start_span("span_1", model="claude-3-opus")
    span.end(status="OK")

    export_path = tmp_path / "telemetry" / "spans.jsonl"
    tracer.export_jsonl(export_path)

    assert export_path.exists()
    lines = export_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["name"] == "span_1"
    assert record["status"]["code"] == "OK"
    assert record["attributes"]["service.name"] == "test-service"
