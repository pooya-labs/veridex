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
