from __future__ import annotations

import ast
import json
import re
from typing import Any, Optional
from veridex.core.models import Assertion, AssertionResult, AssertionType, TestResult
from veridex.evaluators.base import BaseEvaluator


class CodeAndSqlEvaluator(BaseEvaluator):
    """Evaluates code syntax, SQL validity, SQL safety constraints, and JSON path lookups."""

    DANGEROUS_SQL_PATTERNS = [
        (re.compile(r"\bDROP\s+(?:DATABASE|TABLE|SCHEMA)\b", re.IGNORECASE), "Disallowed DROP statement"),
        (re.compile(r"\bTRUNCATE\s+(?:TABLE)?\b", re.IGNORECASE), "Disallowed TRUNCATE statement"),
        (re.compile(r"\bDELETE\s+FROM\s+\w+\s*(?:;|\Z)", re.IGNORECASE), "DELETE without WHERE clause"),
        (re.compile(r"\bUPDATE\s+\w+\s+SET\s+[^;]+(?<!WHERE\s)(?:;|\Z)", re.IGNORECASE), "UPDATE without WHERE clause"),
    ]

    def evaluate(
        self,
        assertion: Assertion,
        output: str,
        test_case_result: Optional[TestResult] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AssertionResult:
        a_type = assertion.type
        cleaned_output = self._extract_code(output)

        if a_type == AssertionType.PYTHON_SYNTAX:
            try:
                ast.parse(cleaned_output)
                return AssertionResult(
                    assertion_type=a_type.value,
                    name=assertion.name or "python_syntax",
                    passed=True,
                    score=1.0,
                    message="Python syntax validated successfully (clean AST).",
                    expected="Valid Python syntax",
                    actual="Syntax OK",
                )
            except SyntaxError as e:
                return AssertionResult(
                    assertion_type=a_type.value,
                    name=assertion.name or "python_syntax",
                    passed=False,
                    score=0.0,
                    message=f"Python syntax error at line {e.lineno}: {e.msg}",
                    expected="Valid Python syntax",
                    actual=f"SyntaxError: {e.msg}",
                )

        elif a_type == AssertionType.VALID_SQL:
            is_valid, reason = self._check_sql_syntax(cleaned_output)
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or "valid_sql",
                passed=is_valid,
                score=1.0 if is_valid else 0.0,
                message=reason,
                expected="Valid SQL statement structure",
                actual="Valid SQL" if is_valid else reason,
            )

        elif a_type == AssertionType.SQL_SAFETY:
            violations = []
            for pattern, desc in self.DANGEROUS_SQL_PATTERNS:
                if pattern.search(cleaned_output):
                    violations.append(desc)

            passed = len(violations) == 0
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or "sql_safety",
                passed=passed,
                score=1.0 if passed else 0.0,
                message="SQL passes safety constraints" if passed else f"Dangerous SQL detected: {', '.join(violations)}",
                expected="Safe parameterized query without unconstrained drops/deletes",
                actual="Safe" if passed else f"Violations: {', '.join(violations)}",
            )

        elif a_type == AssertionType.JSON_PATH:
            return self._evaluate_json_path(assertion, output)

        raise ValueError(f"Unsupported code/SQL assertion type: {a_type}")

    @staticmethod
    def _extract_code(text: str) -> str:
        """Extracts code block from markdown ``` fences if present."""
        stripped = text.strip()
        if "```" in stripped:
            match = re.search(r"```(?:\w+)?\n?(.*?)\n?```", stripped, re.DOTALL)
            if match:
                return match.group(1).strip()
        return stripped

    @staticmethod
    def _check_sql_syntax(sql: str) -> tuple[bool, str]:
        stripped = sql.strip().rstrip(";")
        if not stripped:
            return False, "SQL statement is empty"

        valid_starters = (
            "select", "insert", "update", "delete", "create",
            "with", "alter", "explain", "upsert", "merge"
        )
        first_word = stripped.split()[0].lower()
        if first_word not in valid_starters:
            return False, f"Statement does not begin with standard SQL keyword (starts with '{first_word}')"

        # Check balanced parentheses
        open_count = stripped.count("(")
        close_count = stripped.count(")")
        if open_count != close_count:
            return False, f"Mismatched parentheses: {open_count} '(' vs {close_count} ')'"

        return True, "SQL structure appears well-formed"

    @classmethod
    def _evaluate_json_path(cls, assertion: Assertion, output: str) -> AssertionResult:
        field_path = assertion.field_path or str(assertion.value or "")
        try:
            # Parse json
            cleaned = cls._extract_code(output)
            data = json.loads(cleaned)

            # Traverse path like "user.profile.id" or "items[0].name"
            val = cls._lookup_path(data, field_path)
            passed = val is not None

            # If expected value was provided, check equality
            expected_val = assertion.value if assertion.field_path else None
            if expected_val is not None:
                passed = val == expected_val

            return AssertionResult(
                assertion_type=AssertionType.JSON_PATH.value,
                name=assertion.name or f"json_path({field_path})",
                passed=passed,
                score=1.0 if passed else 0.0,
                message=f"Path '{field_path}' resolved to: {repr(val)}" if passed else f"Path '{field_path}' failed to resolve or match",
                expected=expected_val if expected_val is not None else f"Non-null value at '{field_path}'",
                actual=val,
            )
        except Exception as e:
            return AssertionResult(
                assertion_type=AssertionType.JSON_PATH.value,
                name=assertion.name or f"json_path({field_path})",
                passed=False,
                score=0.0,
                message=f"JSON Path lookup error: {str(e)}",
                expected=field_path,
                actual=output[:100],
            )

    @staticmethod
    def _lookup_path(data: Any, path: str) -> Any:
        tokens = re.split(r"\.|\[(\d+)\]", path)
        curr = data
        for t in tokens:
            if not t:
                continue
            if t.isdigit():
                idx = int(t)
                if isinstance(curr, list) and 0 <= idx < len(curr):
                    curr = curr[idx]
                else:
                    return None
            elif isinstance(curr, dict) and t in curr:
                curr = curr[t]
            else:
                return None
        return curr
