import pytest
from veridex.core.models import Assertion, AssertionType
from veridex.evaluators.similarity import SimilarityEvaluator


@pytest.fixture
def evaluator():
    return SimilarityEvaluator()


def test_levenshtein_similarity(evaluator):
    assertion = Assertion(
        type=AssertionType.LEVENSHTEIN_SIMILARITY,
        value="Machine learning models require data.",
        threshold=0.8,
    )
    # High similarity
    res_high = evaluator.evaluate(assertion, "Machine learning model requires data.")
    assert res_high.passed is True
    assert res_high.score >= 0.8

    # Low similarity
    res_low = evaluator.evaluate(assertion, "Something completely different.")
    assert res_low.passed is False
    assert res_low.score < 0.5


def test_jaccard_and_token_f1(evaluator):
    a_jaccard = Assertion(
        type=AssertionType.JACCARD_SIMILARITY,
        value="distributed systems observability and telemetry",
        threshold=0.6,
    )
    res_j = evaluator.evaluate(a_jaccard, "observability telemetry distributed systems monitoring")
    assert res_j.passed is True

    a_f1 = Assertion(
        type=AssertionType.TOKEN_OVERLAP,
        value="quick brown fox jumps",
        threshold=0.65,
    )
    res_f1 = evaluator.evaluate(a_f1, "the quick brown fox jumped")
    assert res_f1.passed is True
