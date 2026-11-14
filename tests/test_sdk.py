import pytest
from veridex.sdk import assert_eval


def test_assert_eval_success():
    json_output = '{"intent": "book_flight", "destination": "Tokyo"}'
    # Should not raise any exception
    assert_eval(
        output=json_output,
        assertions=[
            "valid_json",
            {"type": "contains", "value": "Tokyo"},
            {"type": "json_path", "field_path": "intent", "value": "book_flight"},
            "no_pii",
        ],
    )


def test_assert_eval_failure():
    invalid_output = "I like apples and contact me at secret@corp.internal"
    with pytest.raises(AssertionError) as exc_info:
        assert_eval(
            output=invalid_output,
            assertions=[
                "valid_json",
                "no_pii",
            ],
        )
    err_str = str(exc_info.value)
    assert "valid_json" in err_str
    assert "no_pii" in err_str
