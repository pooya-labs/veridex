from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from veridex.core.models import TestSuite
from veridex.core.runner import TestRunner
from veridex.core.reporter import ConsoleReporter, JsonReporter, MarkdownReporter
from veridex.core.diff import SuiteComparator
from veridex.loaders.yaml_loader import SuiteLoader


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veridex",
        description="Veridex: Production-grade LLM evaluation, regression testing, and reliability harness.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Execute an evaluation test suite.")
    run_parser.add_argument("suite", type=str, help="Path to YAML or JSON test suite file.")
    run_parser.add_argument("-o", "--output-json", type=str, help="Path to export JSON results.")
    run_parser.add_argument("-m", "--output-md", type=str, help="Path to export Markdown report.")
    run_parser.add_argument("-p", "--provider", type=str, help="Override provider (e.g. mock, openai, gemini).")
    run_parser.add_argument("--model", type=str, help="Override model name.")
    run_parser.add_argument("-c", "--concurrency", type=int, help="Override concurrent execution limit.")
    run_parser.add_argument("--simulate-success", action="store_true", help="Simulate expected outputs when using mock provider.")

    # Command: compare
    comp_parser = subparsers.add_parser("compare", help="Compare two evaluation runs to detect regressions.")
    comp_parser.add_argument("baseline", type=str, help="Path to baseline evaluation JSON file.")
    comp_parser.add_argument("current", type=str, help="Path to current evaluation JSON file.")

    # Command: validate
    val_parser = subparsers.add_parser("validate", help="Validate test suite syntax and assertion schemas.")
    val_parser.add_argument("suite", type=str, help="Path to test suite file.")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Scaffold a new Veridex starter suite.")
    init_parser.add_argument("--dir", type=str, default=".", help="Target directory for starter files.")

    return parser


def handle_run(args: argparse.Namespace, console: Console) -> int:
    suite_path = Path(args.suite)
    if not suite_path.exists():
        console.print(f"[bold red]Error:[/bold red] Suite file '{suite_path}' does not exist.")
        return 1

    try:
        suite = SuiteLoader.load_from_file(suite_path)
    except Exception as e:
        console.print(f"[bold red]Failed to load suite:[/bold red] {e}")
        return 1

    # Overrides
    if args.provider:
        suite.provider = args.provider
    if args.model:
        suite.model = args.model
    if args.concurrency:
        suite.concurrency = args.concurrency

    console.print(f"[cyan]Executing suite '[bold]{suite.name}[/bold]' ({len(suite.cases)} cases)...[/cyan]")

    runner = TestRunner()
    if args.simulate_success and suite.provider == "mock":
        from veridex.providers.mock import MockProvider
        runner.provider = MockProvider(model=suite.model or "mock-model", simulate_success=True)

    result = asyncio.run(runner.run_suite(suite))

    # Console Report
    reporter = ConsoleReporter(console=console)
    reporter.print_summary(result)

    # File exports
    if args.output_json:
        JsonReporter.export(result, args.output_json)
        console.print(f"[green]Saved JSON report to:[/green] {args.output_json}")

    if args.output_md:
        md_text = MarkdownReporter.generate(result)
        Path(args.output_md).write_text(md_text, encoding="utf-8")
        console.print(f"[green]Saved Markdown report to:[/green] {args.output_md}")

    return 0 if result.passed_cases == result.total_cases else 2


def handle_compare(args: argparse.Namespace, console: Console) -> int:
    base_path = Path(args.baseline)
    curr_path = Path(args.current)

    if not base_path.exists() or not curr_path.exists():
        console.print("[bold red]Error:[/bold red] One or both files to compare do not exist.")
        return 1

    try:
        diff = SuiteComparator.compare_files(base_path, curr_path)
        SuiteComparator.print_diff(diff, console=console)
        return 0 if not diff.regressions else 3
    except Exception as e:
        console.print(f"[bold red]Comparison failed:[/bold red] {e}")
        return 1


def handle_validate(args: argparse.Namespace, console: Console) -> int:
    suite_path = Path(args.suite)
    try:
        suite = SuiteLoader.load_from_file(suite_path)
        console.print(f"[bold green]✓ Valid suite format:[/bold green] '{suite.name}' ({len(suite.cases)} test cases configured).")
        return 0
    except Exception as e:
        console.print(f"[bold red]Validation error:[/bold red] {e}")
        return 1


def handle_init(args: argparse.Namespace, console: Console) -> int:
    target_dir = Path(args.dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    starter_yaml = \"\"\"id: starter_eval
name: Starter AI Quality & Guardrails Suite
description: Baseline evaluation suite demonstrating deterministic, similarity, and safety checks.
provider: mock
model: mock-model-v1
concurrency: 5

cases:
  - id: check_json_output
    name: Verify JSON Schema Output
    prompt: "Extract customer intent and entities from: 'I need to cancel my subscription #40291'."
    expected_output: '{"intent": "cancel_subscription", "account_id": 40291}'
    assertions:
      - type: valid_json
      - type: contains
        value: "cancel_subscription"

  - id: check_safety_pii
    name: Verify No PII Leakage
    prompt: "Summarize this account transaction."
    assertions:
      - type: no_pii

  - id: check_similarity
    name: Verify Response Accuracy
    prompt: "What is the capital of France?"
    expected_output: "The capital of France is Paris."
    assertions:
      - type: levenshtein_similarity
        threshold: 0.8
\"\"\"
    output_file = target_dir / "veridex_starter.yaml"
    if output_file.exists():
        console.print(f"[yellow]File already exists at '{output_file}'. Aborted.[/yellow]")
        return 1

    output_file.write_text(starter_yaml, encoding="utf-8")
    console.print(f"[bold green]✓ Initialized starter suite at:[/bold green] {output_file}")
    console.print("Run it with: [cyan]veridex run veridex_starter.yaml[/cyan]")
    return 0


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()
    console = Console()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "run":
        sys.exit(handle_run(args, console))
    elif args.command == "compare":
        sys.exit(handle_compare(args, console))
    elif args.command == "validate":
        sys.exit(handle_validate(args, console))
    elif args.command == "init":
        sys.exit(handle_init(args, console))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
