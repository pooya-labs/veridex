import pytest
from veridex.core.models import Assertion, AssertionType
from veridex.evaluators.rag import RagGroundednessEvaluator


@pytest.fixture
def evaluator():
    return RagGroundednessEvaluator()


def test_rag_faithfulness_grounded(evaluator):
    context = "The Apollo 11 mission landed on the Moon on July 20, 1969. Neil Armstrong was the commander."
    assertion = Assertion(type=AssertionType.FAITHFULNESS, value=context, threshold=0.6)

    # Output strictly grounded in context
    grounded_answer = "Neil Armstrong commanded Apollo 11, which reached the Moon in July 1969."
    res = evaluator.evaluate(assertion, grounded_answer)
    assert res.passed is True
    assert res.score >= 0.6


def test_rag_faithfulness_hallucinated_number(evaluator):
    context = "Refunds take 3 business days."
    assertion = Assertion(type=AssertionType.FAITHFULNESS, value=context, threshold=0.7)

    # Hallucinated different number
    unsupported_answer = "Refunds take 30 business days and cost $50."
    res = evaluator.evaluate(assertion, unsupported_answer)
    # Penalized due to unsupported numbers
    assert res.score < 0.7


def test_rag_answer_relevance(evaluator):
    assertion = Assertion(type=AssertionType.ANSWER_RELEVANCE, threshold=0.5)

    res_relevant = evaluator.evaluate(
        assertion,
        output="The capital of Germany is Berlin.",
        context={"input_prompt": "What is the capital of Germany?"},
    )
    assert res_relevant.passed is True

    res_irrelevant = evaluator.evaluate(
        assertion,
        output="Apples and bananas are sweet fruits.",
        context={"input_prompt": "What is the capital of Germany?"},
    )
    assert res_irrelevant.passed is False
