import pytest
from pathlib import Path
from veridex.loaders.yaml_loader import SuiteLoader


def test_suite_loader(tmp_path: Path):
    yaml_content = """id: temp_suite
name: Temp Benchmark Suite
provider: mock
model: mock-v1
concurrency: 3

cases:
  - id: t1
    name: Test 1
    prompt: "Hello {{ name }}"
    variables:
      name: "World"
    assertions:
      - type: exact_match
        value: "Hello World"
"""
    file_path = tmp_path / "temp_suite.yaml"
    file_path.write_text(yaml_content, encoding="utf-8")

    suite = SuiteLoader.load_from_file(file_path)
    assert suite.id == "temp_suite"
    assert suite.name == "Temp Benchmark Suite"
    assert suite.concurrency == 3
    assert len(suite.cases) == 1
    # Check variable interpolation
    assert suite.cases[0].prompt == "Hello World"
    assert suite.cases[0].assertions[0].type.value == "exact_match"
