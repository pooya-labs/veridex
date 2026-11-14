import pytest
from pathlib import Path
from veridex.loaders.yaml_loader import SuiteLoader


def test_remote_loader_fallback(tmp_path: Path):
    # Verify local source loading via load_from_source
    suite_yaml = """id: local_source_test
name: Local Source Test Suite
cases:
  - id: c1
    name: Case 1
    prompt: "Hello"
    assertions:
      - type: exact_match
        value: "Hello"
"""
    p = tmp_path / "test_source.yaml"
    p.write_text(suite_yaml, encoding="utf-8")

    suite = SuiteLoader.load_from_source(p)
    assert suite.id == "local_source_test"
    assert len(suite.cases) == 1
