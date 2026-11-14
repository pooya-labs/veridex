from __future__ import annotations

import json
import re
from typing import Any, Optional
from veridex.core.models import Assertion, AssertionResult, AssertionType, TestResult
from veridex.evaluators.base import BaseEvaluator


class DeterministicEvaluator(BaseEvaluator):
    """Evaluates deterministic properties (exact matches, regex, JSON validity, constraints)."""

    def evaluate(
        self,
        assertion: Assertion,
        output: str,
        test_case_result: Optional[TestResult] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AssertionResult:
        context = context or {}
        a_type = assertion.type

        if a_type == AssertionType.EXACT_MATCH:
            expected = assertion.value if assertion.value is not None else context.get("expected_output", "")
            passed = output.strip() == str(expected).strip()
            score = 1.0 if passed else 0.0
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or "exact_match",
                passed=passed,
                score=score,
                message="Exact match succeeded" if passed else f"Expected '{expected}', got '{output[:80]}...'",
                expected=expected,
                actual=output,
            )

        elif a_type == AssertionType.CONTAINS:
            expected = str(assertion.value)
            passed = expected in output
            score = 1.0 if passed else 0.0
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or f"contains({expected[:20]})",
                passed=passed,
                score=score,
                message=f"Output contains substring '{expected}'" if passed else f"Substring '{expected}' not found",
                expected=expected,
                actual=output,
            )

        elif a_type == AssertionType.NOT_CONTAINS:
            forbidden = str(assertion.value)
            passed = forbidden not in output
            score = 1.0 if passed else 0.0
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or f"not_contains({forbidden[:20]})",
                passed=passed,
                score=score,
                message=f"Output does not contain '{forbidden}'" if passed else f"Forbidden substring '{forbidden}' was found",
                expected=f"NOT {forbidden}",
                actual=output,
            )

        elif a_type == AssertionType.REGEX:
            pattern = str(assertion.value)
            match = re.search(pattern, output, re.MULTILINE | re.DOTALL)
            passed = match is not None
            score = 1.0 if passed else 0.0
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or f"regex({pattern[:20]})",
                passed=passed,
                score=score,
                message=f"Pattern '{pattern}' matched" if passed else f"Pattern '{pattern}' failed to match",
                expected=pattern,
                actual=output,
            )

        elif a_type == AssertionType.VALID_JSON:
            try:
                # Attempt to find JSON block if wrapped in markdown
                cleaned = self._extract_json(output)
                parsed = json.loads(cleaned)
                return AssertionResult(
                    assertion_type=a_type.value,
                    name=assertion.name or "valid_json",
                    passed=True,
                    score=1.0,
                    message="Output is valid JSON",
                    expected="Valid JSON string",
                    actual=type(parsed).__name__,
                )
            except Exception as e:
                return AssertionResult(
                    assertion_type=a_type.value,
                    name=assertion.name or "valid_json",
                    passed=False,
                    score=0.0,
                    message=f"JSON decoding failed: {str(e)}",
                    expected="Valid JSON string",
                    actual=output[:100],
                )

        elif a_type == AssertionType.JSON_SCHEMA:
            schema = assertion.value
            try:
                cleaned = self._extract_json(output)
                data = json.loads(cleaned)
                errors = self._validate_json_schema(data, schema)
                passed = len(errors) == 0
                return AssertionResult(
                    assertion_type=a_type.value,
                    name=assertion.name or "json_schema",
                    passed=passed,
                    score=1.0 if passed else 0.0,
                    message="JSON Schema validated successfully" if passed else f"Schema violations: {'; '.join(errors)}",
                    expected=schema,
                    actual=data,
                )
            except Exception as e:
                return AssertionResult(
                    assertion_type=a_type.value,
                    name=assertion.name or "json_schema",
                    passed=False,
                    score=0.0,
                    message=f"JSON parsing or schema validation error: {str(e)}",
                    expected=schema,
                    actual=output[:100],
                )

        elif a_type == AssertionType.MAX_LATENCY_MS:
            limit = float(assertion.value or 1000.0)
            latency = test_case_result.latency_ms if test_case_result else 0.0
            passed = latency <= limit
            score = 1.0 if passed else max(0.0, 1.0 - (latency - limit) / limit)
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or f"max_latency({limit}ms)",
                passed=passed,
                score=score,
                message=f"Latency {latency:.1f}ms <= {limit:.1f}ms" if passed else f"Latency {latency:.1f}ms exceeded limit {limit:.1f}ms",
                expected=limit,
                actual=latency,
            )

        elif a_type == AssertionType.MAX_TOKENS:
            limit = int(assertion.value or 500)
            tokens = (
                test_case_result.token_usage.get("total_tokens", 0)
                if test_case_result
                else len(output.split())
            )
            passed = tokens <= limit
            score = 1.0 if passed else 0.0
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or f"max_tokens({limit})",
                passed=passed,
                score=score,
                message=f"Tokens {tokens} <= {limit}" if passed else f"Token count {tokens} exceeded {limit}",
                expected=limit,
                actual=tokens,
            )

        raise ValueError(f"Unsupported deterministic assertion type: {a_type}")

    @staticmethod
    def _extract_json(text: str) -> str:
        """Strips markdown code fences like ```json ... ``` if present."""
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return stripped

    @classmethod
    def _validate_json_schema(cls, data: Any, schema: dict[str, Any], path: str = "root") -> list[str]:
        """Built-in lightweight schema validator for common JSON schema specifications."""
        errors: list[str] = []
        if not isinstance(schema, dict):
            return errors

        # Type check
        expected_type = schema.get("type")
        if expected_type:
            type_mapping = {
                "object": dict,
                "array": list,
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool,
                "null": type(None),
            }
            target_cls = type_mapping.get(expected_type)
            if target_cls and not isinstance(data, target_cls):
                errors.append(f"{path}: expected type '{expected_type}', got '{type(data).__name__}'")
                return errors

        # Object validation
        if isinstance(data, dict):
            required_keys = schema.get("required", [])
            for req in required_keys:
                if req not in data:
                    errors.append(f"{path}: missing required field '{req}'")

            properties = schema.get("properties", {})
            for key, prop_schema in properties.items():
                if key in data:
                    errors.extend(cls._validate_json_schema(data[key], prop_schema, f"{path}.{key}"))

        # Array validation
        elif isinstance(data, list):
            items_schema = schema.get("items")
            if items_schema:
                for idx, item in enumerate(data):
                    errors.extend(cls._validate_json_schema(item, items_schema, f"{path}[{idx}]"))

        return errors
