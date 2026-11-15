from __future__ import annotations

import pytest
from pathlib import Path
from veridex.core.generator import SuiteGenerator
from veridex.core.models import AssertionType, TestSuite
from veridex.core.runner import TestRunner
from veridex.providers.mock import MockProvider


def test_suite_generator_all_archetypes():
    archetypes = ["json", "rag", "safety", "sql", "general"]
    for arch in archetypes:
        suite = SuiteGenerator.generate_suite(
            topic="finance",
            template=arch,
            count=3,
        )
        assert isinstance(suite, TestSuite)
        assert len(suite.cases) == 3
        assert suite.provider == "mock"
        assert arch in suite.id or arch in suite.name.lower()
        for c in suite.cases:
            assert c.prompt
            assert len(c.assertions) >= 2


def test_suite_generator_json_and_yaml_serialization(tmp_path: Path):
    suite = SuiteGenerator.generate_suite(topic="telemetry", template="json", count=2)
    yaml_str = SuiteGenerator.to_yaml(suite)
    assert "telemetry" in yaml_str
    assert "valid_json" in yaml_str

    out_file = tmp_path / "test_suite.yaml"
    saved = SuiteGenerator.save(suite, str(out_file))
    assert Path(saved).exists()
    assert Path(saved).read_text(encoding="utf-8") == yaml_str


def test_suite_generator_execution():
    import asyncio
    async def _run():
        suite = SuiteGenerator.generate_suite(topic="customer_support", template="safety", count=2)
        runner = TestRunner(provider=MockProvider(simulate_success=True))
        result = await runner.run_suite(suite)
        assert result.total_cases == 2
        assert result.passed_cases == 2
        assert result.pass_rate == 1.0

    asyncio.run(_run())
