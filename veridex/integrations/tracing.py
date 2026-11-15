from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union


@dataclass
class VeridexSpan:
    trace_id: str
    span_id: str
    name: str
    start_time_unix_nano: int
    end_time_unix_nano: Optional[int] = None
    duration_ms: float = 0.0
    status: str = "UNSET"  # "OK", "ERROR"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({
            "name": name,
            "timestamp_unix_nano": int(time.time() * 1e9),
            "attributes": attributes or {},
        })

    def end(self, status: str = "OK") -> None:
        self.end_time_unix_nano = int(time.time() * 1e9)
        self.duration_ms = round((self.end_time_unix_nano - self.start_time_unix_nano) / 1e6, 2)
        self.status = status

    def to_otel_dict(self) -> Dict[str, Any]:
        """Format span as OpenTelemetry GenAI Semantic Conventions compliant dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "start_time_unix_nano": self.start_time_unix_nano,
            "end_time_unix_nano": self.end_time_unix_nano,
            "duration_ms": self.duration_ms,
            "status": {"code": self.status},
            "attributes": self.attributes,
            "events": self.events,
        }


class VeridexTracer:
    """
    OpenTelemetry-compatible GenAI evaluation tracer and telemetry exporter.
    Records model latencies, tokens, prompt assertions, and compliance events.
    """

    def __init__(self, service_name: str = "veridex-eval") -> None:
        self.service_name = service_name
        self.spans: List[VeridexSpan] = []

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> VeridexSpan:
        t_id = trace_id or uuid.uuid4().hex
        s_id = uuid.uuid4().hex[:16]
        span = VeridexSpan(
            trace_id=t_id,
            span_id=s_id,
            name=name,
            start_time_unix_nano=int(time.time() * 1e9),
            attributes={
                "service.name": self.service_name,
                "gen_ai.system": provider or "veridex",
                "gen_ai.request.model": model or "unknown",
            },
        )
        if prompt:
            span.set_attribute("gen_ai.prompt", prompt)
        self.spans.append(span)
        return span

    @contextmanager
    def trace(
        self,
        name: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Generator[VeridexSpan, None, None]:
        span = self.start_span(name=name, model=model, provider=provider, prompt=prompt)
        try:
            yield span
            if span.end_time_unix_nano is None:
                span.end(status="OK")
        except Exception as e:
            span.add_event("exception", {"exception.message": str(e), "exception.type": type(e).__name__})
            span.end(status="ERROR")
            raise

    def export_otel(self) -> List[Dict[str, Any]]:
        return [span.to_otel_dict() for span in self.spans]

    def export_jsonl(self, file_path: Union[str, Path]) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for span in self.spans:
                f.write(json.dumps(span.to_otel_dict()) + "\n")
