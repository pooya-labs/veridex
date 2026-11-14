import pytest
from veridex.core.models import SuiteResult, TestResult
from veridex.core.diff import SuiteComparator


def test_regression_diff_detection():
    # Baseline: both case_1 and case_2 passed
    baseline = SuiteResult(
        suite_id="test_suite",
        suite_name="Test Suite",
        provider="mock",
        model="gpt-4o",
        total_cases=2,
        passed_cases=2,
        failed_cases=0,
        pass_rate=1.0,
        average_latency_ms=150.0,
        total_tokens=500,
        total_cost_usd=0.005,
        results=[
            TestResult(case_id="case_1", case_name="C1", passed=True, input_prompt="", output=""),
            TestResult(case_id="case_2", case_name="C2", passed=True, input_prompt="", output=""),
        ],
    )

    # Current: case_1 failed, case_2 passed
    current = SuiteResult(
        suite_id="test_suite",
        suite_name="Test Suite",
        provider="mock",
        model="gemini-flash",
        total_cases=2,
        passed_cases=1,
        failed_cases=1,
        pass_rate=0.5,
        average_latency_ms=80.0,
        total_tokens=480,
        total_cost_usd=0.001,
        results=[
            TestResult(case_id="case_1", case_name="C1", passed=False, input_prompt="", output=""),
            TestResult(case_id="case_2", case_name="C2", passed=True, input_prompt="", output=""),
        ],
    )

    diff = SuiteComparator.compare(baseline, current)

    assert "case_1" in diff.regressions
    assert len(diff.improvements) == 0
    assert diff.pass_rate_delta == -0.5
    assert diff.latency_delta_ms == -70.0
    assert diff.cost_delta_usd < 0.0
