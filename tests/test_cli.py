from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock
from rich.console import Console

from veridex.cli import (
    create_parser,
    handle_validate,
    handle_init,
    handle_matrix,
    handle_fuzz,
    handle_generate,
    handle_compare,
)


def test_cli_parser_construction():
    parser = create_parser()
    assert parser is not None
    args = parser.parse_args(["validate", "examples/01_structured_extraction/suite.yaml"])
    assert args.command == "validate"
    assert args.suite == "examples/01_structured_extraction/suite.yaml"


def test_cli_validate_success():
    console = Console(record=True)
    args = argparse.Namespace(suite="examples/01_structured_extraction/suite.yaml")
    ret = handle_validate(args, console)
    assert ret == 0
    output = console.export_text()
    assert "Valid suite format" in output


def test_cli_validate_failure():
    console = Console(record=True)
    args = argparse.Namespace(suite="non_existent_suite_xyz.yaml")
    ret = handle_validate(args, console)
    assert ret == 1


def test_cli_init(tmp_path: Path):
    console = Console(record=True)
    args = argparse.Namespace(dir=str(tmp_path))
    ret = handle_init(args, console)
    assert ret == 0
    starter_file = tmp_path / "veridex_starter.yaml"
    assert starter_file.exists()
    content = starter_file.read_text(encoding="utf-8")
    assert "Starter AI Quality & Guardrails Suite" in content


def test_cli_matrix():
    console = Console(record=True)
    args = argparse.Namespace(
        suite="examples/01_structured_extraction/suite.yaml",
        models=["mock-v1", "mock-v2"],
        provider="mock",
    )
    ret = handle_matrix(args, console)
    assert ret == 0
    output = console.export_text()
    assert "MODEL COMPARISON MATRIX" in output


def test_cli_fuzz(tmp_path: Path):
    console = Console(record=True)
    out_file = str(tmp_path / "fuzzed.yaml")
    args = argparse.Namespace(
        suite="examples/01_structured_extraction/suite.yaml",
        modes="typo,casing",
        output=out_file,
        run=False,
    )
    ret = handle_fuzz(args, console)
    assert ret == 0
    assert Path(out_file).exists()


def test_cli_generate(tmp_path: Path):
    console = Console(record=True)
    out_file = str(tmp_path / "gen_suite.yaml")
    args = argparse.Namespace(
        topic="customer_support",
        template="json",
        cases=2,
        output=out_file,
        run=True,
        simulate_success=True,
    )
    ret = handle_generate(args, console)
    assert ret == 0
    assert Path(out_file).exists()
    output = console.export_text()
    assert "Synthesized test suite" in output
    assert "VERIDEX EVALUATION REPORT" in output


def test_cli_compare_with_markdown_export(tmp_path: Path):
    import json
    console = Console(record=True)
    base_file = tmp_path / "base.json"
    curr_file = tmp_path / "curr.json"
    md_out = tmp_path / "diff.md"

    base_data = {
        "suite_id": "test",
        "suite_name": "Test",
        "provider": "mock",
        "model": "gpt-4o",
        "total_cases": 1,
        "passed_cases": 1,
        "failed_cases": 0,
        "pass_rate": 1.0,
        "average_latency_ms": 100.0,
        "total_tokens": 100,
        "total_cost_usd": 0.001,
        "results": [
            {"case_id": "c1", "case_name": "C1", "passed": True, "input_prompt": "", "output": ""}
        ]
    }
    curr_data = dict(base_data)
    curr_data["passed_cases"] = 0
    curr_data["failed_cases"] = 1
    curr_data["pass_rate"] = 0.0
    curr_data["results"] = [
        {"case_id": "c1", "case_name": "C1", "passed": False, "input_prompt": "", "output": ""}
    ]

    base_file.write_text(json.dumps(base_data), encoding="utf-8")
    curr_file.write_text(json.dumps(curr_data), encoding="utf-8")

    args = argparse.Namespace(
        baseline=str(base_file),
        current=str(curr_file),
        output_md=str(md_out),
        github_summary=False,
        fail_on_regression=True,
    )

    ret = handle_compare(args, console)
    assert ret == 3  # regression detected
    assert md_out.exists()
    md_text = md_out.read_text(encoding="utf-8")
    assert "Veridex LLM Evaluation & Regression Diff" in md_text
    assert "Regressions Detected" in md_text
