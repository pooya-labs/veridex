from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from veridex.core.models import SuiteResult


class ConsoleReporter:
    """Renders high-fidelity evaluation reports to the terminal using Rich."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def print_summary(self, result: SuiteResult) -> None:
        self.console.print()

        # Header Title
        title = f"[bold cyan]VERIDEX EVALUATION REPORT[/bold cyan] :sparkles: [dim]({result.suite_name})[/dim]"
        self.console.print(Panel(title, expand=False, border_style="cyan"))

        # Table of Test Cases
        table = Table(title="Test Case Breakdown", show_header=True, header_style="bold magenta")
        table.add_column("Status", width=10, justify="center")
        table.add_column("Case ID", style="dim", width=18)
        table.add_column("Name", width=30)
        table.add_column("Latency", justify="right", width=12)
        table.add_column("Tokens", justify="right", width=10)
        table.add_column("Assertions", justify="center", width=12)

        for case in result.results:
            status_text = "[bold green]PASS[/bold green]" if case.passed else "[bold red]FAIL[/bold red]"
            latency_str = f"{case.latency_ms:.1f}ms"
            total_toks = str(case.token_usage.get("total_tokens", 0))

            passed_a = sum(1 for a in case.assertion_results if a.passed)
            total_a = len(case.assertion_results)
            a_str = f"{passed_a}/{total_a}"

            table.add_row(
                status_text,
                case.case_id,
                case.case_name,
                latency_str,
                total_toks,
                a_str,
            )

        self.console.print(table)
        self.console.print()

        # Failure Details Section (if any failed)
        failures = [c for c in result.results if not c.passed]
        if failures:
            self.console.print("[bold red]FAILURE DETAILS & DIAGNOSTICS:[/bold red]")
            for f in failures:
                fail_panel_content = Text()
                fail_panel_content.append(f"Prompt: {f.input_prompt}\n", style="dim")
                if f.error:
                    fail_panel_content.append(f"Error: {f.error}\n", style="bold red")

                for a in f.assertion_results:
                    if not a.passed:
                        fail_panel_content.append(f"  ✗ [{a.assertion_type}] {a.message}\n", style="red")
                        if a.expected is not None:
                            fail_panel_content.append(f"    Expected: {str(a.expected)[:80]}\n", style="yellow")
                        if a.actual is not None:
                            fail_panel_content.append(f"    Actual:   {str(a.actual)[:80]}\n", style="white")

                self.console.print(
                    Panel(
                        fail_panel_content,
                        title=f"[red]Failed: {f.case_id} — {f.case_name}[/red]",
                        border_style="red",
                    )
                )

        # Metrics Summary Panel
        pass_color = "green" if result.pass_rate >= 0.8 else "yellow" if result.pass_rate >= 0.5 else "red"
        stats_text = (
            f"Provider: [bold]{result.provider}[/bold] ({result.model}) | "
            f"Pass Rate: [bold {pass_color}]{result.pass_rate * 100:.1f}%[/bold {pass_color}] "
            f"({result.passed_cases}/{result.total_cases}) | "
            f"Avg Latency: [bold]{result.average_latency_ms:.1f}ms[/bold] | "
            f"Est. Cost: [bold]${result.total_cost_usd:.4f}[/bold]"
        )
        self.console.print(Panel(stats_text, title="Aggregate Metrics", border_style="blue"))
        self.console.print()


class JsonReporter:
    """Exports test suite results to JSON file format."""

    @staticmethod
    def export(result: SuiteResult, output_path: Union[str, Path]) -> None:
        path = Path(output_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))


class MarkdownReporter:
    """Generates markdown reports suitable for GitHub PR comments and documentation."""

    @staticmethod
    def generate(result: SuiteResult) -> str:
        pass_badge = "🟢 PASS" if result.pass_rate == 1.0 else ("🟡 PARTIAL" if result.pass_rate >= 0.7 else "🔴 FAIL")

        lines = [
            f"# Veridex Evaluation Report: `{result.suite_name}`",
            f"**Status:** {pass_badge} &nbsp;|&nbsp; **Date:** {result.timestamp}",
            "",
            "## Summary Metrics",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| **Pass Rate** | **{result.pass_rate * 100:.1f}%** ({result.passed_cases}/{result.total_cases}) |",
            f"| **Provider / Model** | `{result.provider}` (`{result.model}`) |",
            f"| **Average Latency** | `{result.average_latency_ms:.1f} ms` |",
            f"| **Total Tokens** | `{result.total_tokens}` |",
            f"| **Estimated Cost** | `${result.total_cost_usd:.4f}` |",
            "",
            "## Test Cases",
            "",
            "| Status | ID | Name | Latency | Assertions |",
            "|:---:|---|---|:---:|:---:|",
        ]

        for case in result.results:
            st = "✅ PASS" if case.passed else "❌ FAIL"
            passed_a = sum(1 for a in case.assertion_results if a.passed)
            total_a = len(case.assertion_results)
            lines.append(f"| {st} | `{case.case_id}` | {case.case_name} | {case.latency_ms:.1f}ms | {passed_a}/{total_a} |")

        lines.append("")
        return "\n".join(lines)


class JunitReporter:
    """Generates standard JUnit XML reports for Jenkins, GitLab CI, GitHub Actions, and Azure DevOps."""

    @staticmethod
    def generate(result: SuiteResult) -> str:
        import html
        total_time_sec = sum(c.latency_ms for c in result.results) / 1000.0
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<testsuites name="Veridex" tests="{result.total_cases}" failures="{result.failed_cases}" errors="0" time="{total_time_sec:.3f}">',
            f'  <testsuite name="{html.escape(result.suite_name)}" tests="{result.total_cases}" failures="{result.failed_cases}" errors="0" time="{total_time_sec:.3f}" timestamp="{result.timestamp}">',
        ]
        for case in result.results:
            case_time = case.latency_ms / 1000.0
            lines.append(f'    <testcase classname="{html.escape(result.suite_name)}" name="{html.escape(case.case_name)}" time="{case_time:.3f}">')
            if not case.passed:
                failed_assertions = [a for a in case.assertion_results if not a.passed]
                fail_msgs = "; ".join(a.message for a in failed_assertions)
                lines.append(f'      <failure message="{html.escape(fail_msgs)}">')
                lines.append(f'Input: {html.escape(case.input_prompt)}')
                lines.append(f'Output: {html.escape(case.output)}')
                for fa in failed_assertions:
                    lines.append(f'Assertion [{html.escape(str(fa.assertion_type))}]: {html.escape(fa.message)}')
                lines.append('      </failure>')
            lines.append('    </testcase>')
        lines.append('  </testsuite>')
        lines.append('</testsuites>')
        return "\n".join(lines)

    @classmethod
    def save(cls, result: SuiteResult, output_path: Union[str, Path]) -> None:
        path = Path(output_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(cls.generate(result))
