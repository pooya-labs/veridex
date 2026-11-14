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
from veridex.core.html_reporter import HtmlReporter
from veridex.core.diff import SuiteComparator
from veridex.core.matrix import MatrixRunner
from veridex.core.fuzzer import SuiteFuzzer
from veridex.loaders.yaml_loader import SuiteLoader


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veridex",
        description="Veridex: Production-grade LLM evaluation, regression testing, and reliability harness.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Execute an evaluation test suite.")
    run_parser.add_argument("suite", type=str, help="Path or URL to YAML or JSON test suite file.")
    run_parser.add_argument("-o", "--output-json", type=str, help="Path to export JSON results.")
    run_parser.add_argument("-m", "--output-md", type=str, help="Path to export Markdown report.")
    run_parser.add_argument("-H", "--output-html", type=str, help="Path to export interactive HTML dashboard report.")
    run_parser.add_argument("-p", "--provider", type=str, help="Override provider (e.g. mock, openai, gemini, http).")
    run_parser.add_argument("-u", "--endpoint-url", type=str, help="Endpoint URL when using HTTP/webhook provider.")
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

    # Command: matrix
    mat_parser = subparsers.add_parser("matrix", help="Run benchmark matrix comparing multiple models.")
    mat_parser.add_argument("suite", type=str, help="Path or URL to test suite file.")
    mat_parser.add_argument("-m", "--models", nargs="+", required=True, help="List of model names to benchmark.")
    mat_parser.add_argument("-p", "--provider", type=str, help="Provider name (e.g. mock, openai, gemini).")

    # Command: fuzz
    fuzz_parser = subparsers.add_parser("fuzz", help="Generate stress-test fuzzed variants of test suite.")
    fuzz_parser.add_argument("suite", type=str, help="Path to test suite file.")
    fuzz_parser.add_argument("--modes", type=str, default="typo,casing,noise,adversarial", help="Comma-separated fuzzing modes.")
    fuzz_parser.add_argument("-o", "--output", type=str, help="Path to save generated fuzzed suite YAML.")
    fuzz_parser.add_argument("--run", action="store_true", help="Execute fuzzed suite immediately.")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Scaffold a new Veridex starter suite.")
    init_parser.add_argument("--dir", type=str, default=".", help="Target directory for starter files.")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Launch local Veridex Studio interactive web dashboard.")
    serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1).")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080).")

    return parser


def handle_run(args: argparse.Namespace, console: Console) -> int:
    suite_source = args.suite

    try:
        suite = SuiteLoader.load_from_source(suite_source)
    except Exception as e:
        console.print(f"[bold red]Failed to load suite:[/bold red] {e}")
        return 1

    # Overrides
    if args.provider:
        suite.provider = args.provider
    if args.endpoint_url:
        suite.endpoint_url = args.endpoint_url
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

    if args.output_html:
        HtmlReporter.export(result, args.output_html)
        console.print(f"[green]Saved Interactive HTML report to:[/green] {args.output_html}")

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
    suite_source = args.suite
    try:
        suite = SuiteLoader.load_from_source(suite_source)
        console.print(f"[bold green]✓ Valid suite format:[/bold green] '{suite.name}' ({len(suite.cases)} test cases configured).")
        return 0
    except Exception as e:
        console.print(f"[bold red]Validation error:[/bold red] {e}")
        return 1


def handle_matrix(args: argparse.Namespace, console: Console) -> int:
    try:
        suite = SuiteLoader.load_from_source(args.suite)
        models: list[str] = []
        for m in args.models:
            models.extend([item.strip() for item in m.split(",") if item.strip()])
        console.print(f"[cyan]Running Benchmark Matrix across {len(models)} models...[/cyan]")
        matrix = asyncio.run(MatrixRunner.run_matrix(suite, models=models, provider_name=args.provider))
        MatrixRunner.print_matrix(matrix, console=console)
        return 0
    except Exception as e:
        console.print(f"[bold red]Matrix run failed:[/bold red] {e}")
        return 1


def handle_fuzz(args: argparse.Namespace, console: Console) -> int:
    try:
        suite = SuiteLoader.load_from_source(args.suite)
        modes = [m.strip() for m in args.modes.split(",") if m.strip()]
        fuzzed = SuiteFuzzer.fuzz_suite(suite, modes=modes)
        console.print(f"[green]✓ Generated fuzzed suite with {len(fuzzed.cases)} cases (expanded from {len(suite.cases)}).[/green]")

        if args.output:
            import yaml
            dumped = yaml.safe_dump(fuzzed.model_dump(mode="json"), sort_keys=False)
            Path(args.output).write_text(dumped, encoding="utf-8")
            console.print(f"[green]Saved fuzzed suite to:[/green] {args.output}")

        if args.run:
            runner = TestRunner()
            res = asyncio.run(runner.run_suite(fuzzed))
            reporter = ConsoleReporter(console=console)
            reporter.print_summary(res)

        return 0
    except Exception as e:
        console.print(f"[bold red]Fuzzing failed:[/bold red] {e}")
        return 1


def handle_init(args: argparse.Namespace, console: Console) -> int:
    target_dir = Path(args.dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    starter_yaml = """id: starter_eval
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
"""
    output_file = target_dir / "veridex_starter.yaml"
    if output_file.exists():
        console.print(f"[yellow]File already exists at '{output_file}'. Aborted.[/yellow]")
        return 1

    output_file.write_text(starter_yaml, encoding="utf-8")
    console.print(f"[bold green]✓ Initialized starter suite at:[/bold green] {output_file}")
    console.print("Run it with: [cyan]veridex run veridex_starter.yaml[/cyan]")
    return 0


def handle_serve(args: argparse.Namespace, console: Console) -> int:
    from veridex.server import run_studio_server
    try:
        run_studio_server(host=args.host, port=args.port)
        return 0
    except Exception as e:
        console.print(f"[bold red]Studio server error:[/bold red] {e}")
        return 1


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
    elif args.command == "matrix":
        sys.exit(handle_matrix(args, console))
    elif args.command == "fuzz":
        sys.exit(handle_fuzz(args, console))
    elif args.command == "init":
        sys.exit(handle_init(args, console))
    elif args.command == "serve":
        sys.exit(handle_serve(args, console))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
