from __future__ import annotations

import asyncio
import time
from typing import Callable, Optional
from veridex.core.models import (
    AssertionResult,
    SuiteResult,
    TestCase,
    TestResult,
    TestSuite,
)
from veridex.evaluators import EvaluatorRegistry
from veridex.providers import BaseProvider, get_provider


class TestRunner:
    """Asynchronous execution engine for Veridex test suites."""
    __test__ = False

    def __init__(
        self,
        provider: Optional[BaseProvider] = None,
        evaluator_registry: Optional[EvaluatorRegistry] = None,
    ) -> None:
        self.provider = provider
        self.evaluator_registry = evaluator_registry or EvaluatorRegistry()

    async def run_suite(
        self,
        suite: TestSuite,
        progress_callback: Optional[Callable[[TestResult, int, int], None]] = None,
    ) -> SuiteResult:
        # Resolve provider
        provider = self.provider or get_provider(
            provider_name=suite.provider,
            model=suite.model,
            endpoint_url=suite.endpoint_url,
        )

        semaphore = asyncio.Semaphore(suite.concurrency)
        total_cases = len(suite.cases)
        completed_count = 0
        results: list[TestResult] = []

        async def _execute_case(case: TestCase) -> TestResult:
            nonlocal completed_count
            async with semaphore:
                test_result = await self._run_single_case(suite, case, provider)
                completed_count += 1
                if progress_callback:
                    progress_callback(test_result, completed_count, total_cases)
                return test_result

        # Run all test cases with controlled concurrency
        tasks = [_execute_case(case) for case in suite.cases]
        results = await asyncio.gather(*tasks)

        # Aggregate statistics
        passed_cases = sum(1 for r in results if r.passed)
        failed_cases = total_cases - passed_cases
        pass_rate = (passed_cases / total_cases) if total_cases > 0 else 0.0

        latencies = [r.latency_ms for r in results if r.latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        total_tokens = sum(r.token_usage.get("total_tokens", 0) for r in results)
        total_cost = sum(r.estimated_cost_usd for r in results)

        return SuiteResult(
            suite_id=suite.id,
            suite_name=suite.name,
            provider=suite.provider,
            model=suite.model or provider.model,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            pass_rate=round(pass_rate, 4),
            average_latency_ms=round(avg_latency, 2),
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            results=results,
            metadata={"concurrency": suite.concurrency},
        )

    async def _run_single_case(
        self,
        suite: TestSuite,
        case: TestCase,
        provider: BaseProvider,
    ) -> TestResult:
        sys_prompt = case.system_prompt or suite.system_prompt
        start_time = time.perf_counter()

        try:
            # Request completion from LLM provider
            resp = await asyncio.wait_for(
                provider.generate(
                    prompt=case.prompt,
                    system_prompt=sys_prompt,
                    temperature=suite.temperature or 0.0,
                    max_tokens=suite.max_tokens or 1024,
                    expected_output=case.expected_output,
                ),
                timeout=suite.timeout_seconds,
            )

            latency_ms = resp.latency_ms or (time.perf_counter() - start_time) * 1000.0
            token_usage = {
                "prompt_tokens": resp.prompt_tokens,
                "completion_tokens": resp.completion_tokens,
                "total_tokens": resp.total_tokens,
            }
            cost_usd = resp.estimated_cost_usd
            output = resp.text
            error_msg = None

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            token_usage = {}
            cost_usd = 0.0
            output = ""
            error_msg = f"Provider invocation error: {str(e)}"

        intermediate_result = TestResult(
            case_id=case.id,
            case_name=case.name,
            passed=False,
            input_prompt=case.prompt,
            system_prompt=sys_prompt,
            output=output,
            latency_ms=latency_ms,
            token_usage=token_usage,
            estimated_cost_usd=cost_usd,
            assertion_results=[],
            error=error_msg,
        )

        if error_msg:
            return intermediate_result

        # Evaluate assertions
        assertion_results: list[AssertionResult] = []
        all_passed = True

        eval_context = {
            "expected_output": case.expected_output,
            "input_prompt": case.prompt,
            "variables": case.variables,
        }

        for assertion in case.assertions:
            res = self.evaluator_registry.evaluate(
                assertion=assertion,
                output=output,
                test_case_result=intermediate_result,
                context=eval_context,
            )
            assertion_results.append(res)
            if not res.passed:
                all_passed = False

        intermediate_result.passed = all_passed
        intermediate_result.assertion_results = assertion_results
        return intermediate_result
