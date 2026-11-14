import pytest
from veridex.core.models import Assertion, AssertionType
from veridex.evaluators.code_and_sql import CodeAndSqlEvaluator


@pytest.fixture
def evaluator():
    return CodeAndSqlEvaluator()


def test_python_syntax_validation(evaluator):
    assertion = Assertion(type=AssertionType.PYTHON_SYNTAX)

    # Valid Python code inside markdown
    valid_code = "```python\ndef calculate(a: int, b: int) -> int:\n    return a + b\n```"
    res_valid = evaluator.evaluate(assertion, valid_code)
    assert res_valid.passed is True
    assert res_valid.score == 1.0

    # Invalid Python syntax
    invalid_code = "def broken(a, b\n    return a +"
    res_invalid = evaluator.evaluate(assertion, invalid_code)
    assert res_invalid.passed is False
    assert res_invalid.score == 0.0


def test_sql_validity_and_safety(evaluator):
    a_valid = Assertion(type=AssertionType.VALID_SQL)
    a_safe = Assertion(type=AssertionType.SQL_SAFETY)

    # Safe SELECT statement
    safe_sql = "SELECT id, email, created_at FROM users WHERE active = true ORDER BY id DESC;"
    assert evaluator.evaluate(a_valid, safe_sql).passed is True
    assert evaluator.evaluate(a_safe, safe_sql).passed is True

    # Dangerous DROP statement
    drop_sql = "DROP TABLE users;"
    assert evaluator.evaluate(a_safe, drop_sql).passed is False

    # Dangerous unconstrained DELETE
    delete_sql = "DELETE FROM orders;"
    assert evaluator.evaluate(a_safe, delete_sql).passed is False


def test_json_path_extraction(evaluator):
    payload = """{
      "status": 200,
      "data": {
        "user": {
          "id": 42,
          "role": "admin"
        },
        "tags": ["alpha", "beta"]
      }
    }"""

    # Check existing nested path
    a_path = Assertion(type=AssertionType.JSON_PATH, field_path="data.user.role", value="admin")
    res = evaluator.evaluate(a_path, payload)
    assert res.passed is True
    assert res.actual == "admin"

    # Check non-existent path
    a_missing = Assertion(type=AssertionType.JSON_PATH, field_path="data.missing.key")
    res_missing = evaluator.evaluate(a_missing, payload)
    assert res_missing.passed is False
