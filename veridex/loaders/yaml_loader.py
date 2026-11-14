from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union
import httpx
import yaml
from veridex.core.models import Assertion, AssertionType, TestCase, TestSuite


class SuiteLoader:
    """Loads and validates Veridex test suites from local files or remote URLs (YAML/JSON)."""

    @classmethod
    def load_from_source(cls, source: Union[str, Path]) -> TestSuite:
        source_str = str(source).strip()

        # Handle remote URL
        if source_str.startswith("http://") or source_str.startswith("https://"):
            return cls.load_from_url(source_str)

        # Handle local file
        return cls.load_from_file(source)

    @classmethod
    def load_from_url(cls, url: str) -> TestSuite:
        """Fetches and parses a test suite definition directly from a remote HTTP(S) URL."""
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content = resp.text

        raw_data = yaml.safe_load(content)
        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid suite format from {url}: expected a dictionary root.")

        return cls.parse_suite_dict(raw_data)

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> TestSuite:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Suite file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML/JSON
        raw_data = yaml.safe_load(content)
        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid suite format in {path}: expected a dictionary root.")

        base_dir = path.parent
        return cls.parse_suite_dict(raw_data, base_dir=base_dir)

    @classmethod
    def parse_suite_dict(cls, data: Dict[str, Any], base_dir: Optional[Path] = None) -> TestSuite:
        suite_id = data.get("id") or data.get("name", "suite").lower().replace(" ", "_")
        name = data.get("name", "Untitled Suite")
        description = data.get("description")
        provider = data.get("provider", "mock")
        model = data.get("model")
        endpoint_url = data.get("endpoint_url") or data.get("url")
        matrix_models = data.get("matrix_models") or data.get("models") or []
        temperature = data.get("temperature", 0.0)
        max_tokens = data.get("max_tokens", 1024)
        system_prompt = data.get("system_prompt")
        concurrency = data.get("concurrency", 5)
        timeout_seconds = data.get("timeout_seconds", 30.0)

        raw_cases = data.get("cases") or data.get("tests") or []
        cases: list[TestCase] = []

        for idx, case_data in enumerate(raw_cases):
            case_id = case_data.get("id", f"case_{idx+1}")
            case_name = case_data.get("name", f"Test Case {idx+1}")
            desc = case_data.get("description")
            prompt = case_data.get("prompt", "")
            sys_prompt = case_data.get("system_prompt")
            variables = case_data.get("variables", {})
            expected = case_data.get("expected_output") or case_data.get("expected")
            tags = case_data.get("tags", [])
            metadata = case_data.get("metadata", {})

            # Parse assertions
            assertions: list[Assertion] = []
            raw_assertions = case_data.get("assertions", [])
            for raw_a in raw_assertions:
                if isinstance(raw_a, str):
                    # shorthand e.g. "valid_json" or "no_pii"
                    assertions.append(Assertion(type=AssertionType(raw_a)))
                elif isinstance(raw_a, dict):
                    a_type_str = raw_a.get("type")
                    if not a_type_str:
                        raise ValueError(f"Assertion missing 'type' field in test case '{case_id}'")

                    a_val = raw_a.get("value")

                    # Handle external schema files
                    schema_file = raw_a.get("schema_file")
                    if schema_file and base_dir:
                        schema_path = base_dir / schema_file
                        if schema_path.exists():
                            with open(schema_path, "r", encoding="utf-8") as sf:
                                a_val = json.load(sf)

                    assertions.append(
                        Assertion(
                            type=AssertionType(a_type_str),
                            value=a_val,
                            threshold=float(raw_a.get("threshold", 1.0)),
                            rubric=raw_a.get("rubric"),
                            field_path=raw_a.get("field_path"),
                            weight=float(raw_a.get("weight", 1.0)),
                            name=raw_a.get("name"),
                        )
                    )

            # Templating interpolation if variables provided
            if variables:
                prompt = cls._interpolate(prompt, variables)
                if expected:
                    expected = cls._interpolate(str(expected), variables)

            cases.append(
                TestCase(
                    id=case_id,
                    name=case_name,
                    description=desc,
                    prompt=prompt,
                    system_prompt=sys_prompt,
                    variables=variables,
                    expected_output=expected,
                    assertions=assertions,
                    tags=tags,
                    metadata=metadata,
                )
            )

        return TestSuite(
            id=suite_id,
            name=name,
            description=description,
            provider=provider,
            model=model,
            endpoint_url=endpoint_url,
            matrix_models=matrix_models,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            cases=cases,
            concurrency=concurrency,
            timeout_seconds=timeout_seconds,
        )

    @staticmethod
    def _interpolate(text: str, variables: Dict[str, Any]) -> str:
        """Interpolates variables like {{ key }} or ${key}."""
        result = text
        for k, v in variables.items():
            result = result.replace(f"{{{{ {k} }}}}", str(v))
            result = result.replace(f"{{{{{k}}}}}", str(v))
            result = result.replace(f"${{{k}}}", str(v))
        return result
