import pytest
from veridex.core.models import Assertion, AssertionType
from veridex.evaluators.deterministic import DeterministicEvaluator


@pytest.fixture
def evaluator():
    return DeterministicEvaluator()


def test_exact_match(evaluator):
    assertion = Assertion(type=AssertionType.EXACT_MATCH, value="Hello World")
    res_pass = evaluator.evaluate(assertion, "Hello World")
    assert res_pass.passed is True
    assert res_pass.score == 1.0

    res_fail = evaluator.evaluate(assertion, "Goodbye World")
    assert res_fail.passed is False
    assert res_fail.score == 0.0


def test_contains_and_not_contains(evaluator):
    a_contains = Assertion(type=AssertionType.CONTAINS, value="apple")
    assert evaluator.evaluate(a_contains, "I like apples").passed is True
    assert evaluator.evaluate(a_contains, "I like oranges").passed is False

    a_not_contains = Assertion(type=AssertionType.NOT_CONTAINS, value="banana")
    assert evaluator.evaluate(a_not_contains, "I like apples").passed is True
    assert evaluator.evaluate(a_not_contains, "I like bananas").passed is False


def test_regex_matching(evaluator):
    assertion = Assertion(type=AssertionType.REGEX, value=r"\b[A-Z]{3}-\d{4}\b")
    assert evaluator.evaluate(assertion, "Your ticket is TCK-1234.").passed is True
    assert evaluator.evaluate(assertion, "Your ticket is 1234-TCK.").passed is False


def test_valid_json_and_schema(evaluator):
    a_json = Assertion(type=AssertionType.VALID_JSON)
    assert evaluator.evaluate(a_json, '{"key": "value", "num": 42}').passed is True
    assert evaluator.evaluate(a_json, "```json\n{\"key\": \"value\"}\n```").passed is True
    assert evaluator.evaluate(a_json, "not valid json {broken").passed is False

    schema = {
        "type": "object",
        "required": ["name", "score"],
        "properties": {
            "name": {"type": "string"},
            "score": {"type": "number"},
        },
    }
    a_schema = Assertion(type=AssertionType.JSON_SCHEMA, value=schema)
    assert evaluator.evaluate(a_schema, '{"name": "Alice", "score": 98.5}').passed is True
    # Missing required field
    assert evaluator.evaluate(a_schema, '{"name": "Alice"}').passed is False
