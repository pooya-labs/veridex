import asyncio
from veridex.core.models import Assertion, AssertionType, TestCase, TestSuite
from veridex.core.runner import TestRunner
from veridex.providers.mock import MockProvider


def test_runner_execution():
    async def _run():
        provider = MockProvider(
            responses={
                "ping": "pong",
                "get_status": '{"status": "ok"}',
            }
        )

        suite = TestSuite(
            id="test_suite_1",
            name="Unit Test Suite",
            provider="mock",
            concurrency=2,
            cases=[
                TestCase(
                    id="case_1",
                    name="Check Ping Pong",
                    prompt="ping",
                    expected_output="pong",
                    assertions=[
                        Assertion(type=AssertionType.EXACT_MATCH, value="pong"),
                    ],
                ),
                TestCase(
                    id="case_2",
                    name="Check Status JSON",
                    prompt="get_status",
                    assertions=[
                        Assertion(type=AssertionType.VALID_JSON),
                        Assertion(type=AssertionType.CONTAINS, value="ok"),
                    ],
                ),
            ],
        )

        runner = TestRunner(provider=provider)
        result = await runner.run_suite(suite)

        assert result.total_cases == 2
        assert result.passed_cases == 2
        assert result.failed_cases == 0
        assert result.pass_rate == 1.0
        assert len(result.results) == 2
        assert result.results[0].passed is True
        assert result.results[1].passed is True

    asyncio.run(_run())
