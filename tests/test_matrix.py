import asyncio
import pytest
from veridex.core.models import Assertion, AssertionType, TestCase, TestSuite
from veridex.core.matrix import MatrixRunner


def test_matrix_runner_multi_model():
    suite = TestSuite(
        id="matrix_eval",
        name="Matrix Evaluation",
        provider="mock",
        cases=[
            TestCase(
                id="c1",
                name="Ping Test",
                prompt="ping",
                expected_output="Mock completion response.",
                assertions=[
                    Assertion(type=AssertionType.EXACT_MATCH, value="Mock completion response."),
                ],
            )
        ],
    )

    models = ["mock-model-alpha", "mock-model-beta"]
    matrix = asyncio.run(MatrixRunner.run_matrix(suite, models=models, provider_name="mock"))

    assert len(matrix.model_results) == 2
    assert "mock-model-alpha" in matrix.model_results
    assert "mock-model-beta" in matrix.model_results
    assert matrix.best_model_by_pass_rate is not None
