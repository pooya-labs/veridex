from __future__ import annotations

import asyncio
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from veridex.core.models import SuiteResult, TestSuite
from veridex.core.runner import TestRunner
from veridex.providers import get_provider


class MatrixResult(BaseModel):
    suite_id: str
    suite_name: str
    model_results: Dict[str, SuiteResult] = Field(default_factory=dict)
    best_model_by_pass_rate: Optional[str] = None
    fastest_model: Optional[str] = None


class MatrixRunner:
    """Executes a test suite across a matrix of multiple models/providers to compare performance."""

    @classmethod
    async def run_matrix(
        cls,
        suite: TestSuite,
        models: List[str],
        provider_name: Optional[str] = None,
    ) -> MatrixResult:
        model_results: Dict[str, SuiteResult] = {}
        prov = provider_name or suite.provider

        for model in models:
            target_suite = suite.model_copy(deep=True)
            target_suite.model = model
            target_suite.provider = prov

            provider_instance = get_provider(
                provider_name=prov,
                model=model,
                endpoint_url=suite.endpoint_url,
            )

            runner = TestRunner(provider=provider_instance)
            res = await runner.run_suite(target_suite)
            model_results[model] = res

        # Determine best models
        best_pass = max(model_results.keys(), key=lambda m: model_results[m].pass_rate) if model_results else None
        fastest = min(model_results.keys(), key=lambda m: model_results[m].average_latency_ms) if model_results else None

        return MatrixResult(
            suite_id=suite.id,
            suite_name=suite.name,
            model_results=model_results,
            best_model_by_pass_rate=best_pass,
            fastest_model=fastest,
        )

    @classmethod
    def print_matrix(cls, matrix: MatrixResult, console: Optional[Console] = None) -> None:
        console = console or Console()
        console.print()

        title = f"[bold cyan]VERIDEX MODEL COMPARISON MATRIX[/bold cyan] :trophy: [dim]({matrix.suite_name})[/dim]"
        console.print(Panel(title, expand=False, border_style="cyan"))

        # Leaderboard Table
        lb_table = Table(title="Model Leaderboard", show_header=True, header_style="bold magenta")
        lb_table.add_column("Rank", justify="center", width=6)
        lb_table.add_column("Model", style="bold", width=24)
        lb_table.add_column("Pass Rate", justify="right", width=14)
        lb_table.add_column("Passed / Total", justify="center", width=16)
        lb_table.add_column("Avg Latency", justify="right", width=14)
        lb_table.add_column("Total Cost", justify="right", width=14)

        # Sort by pass rate desc, then latency asc
        sorted_models = sorted(
            matrix.model_results.items(),
            key=lambda item: (item[1].pass_rate, -item[1].average_latency_ms),
            reverse=True,
        )

        for rank, (model_name, res) in enumerate(sorted_models, start=1):
            color = "green" if res.pass_rate >= 0.8 else ("yellow" if res.pass_rate >= 0.5 else "red")
            rate_str = f"[{color}]{res.pass_rate * 100:.1f}%[/{color}]"
            passed_str = f"{res.passed_cases}/{res.total_cases}"
            lat_str = f"{res.average_latency_ms:.1f}ms"
            cost_str = f"${res.total_cost_usd:.4f}"

            lb_table.add_row(
                str(rank),
                model_name,
                rate_str,
                passed_str,
                lat_str,
                cost_str,
            )

        console.print(lb_table)
        console.print()

        # Case-by-Case Breakdown
        case_table = Table(title="Case-by-Case Cross-Evaluation", show_header=True)
        case_table.add_column("Case ID", style="dim", width=20)

        model_names = list(matrix.model_results.keys())
        for m in model_names:
            case_table.add_column(m, justify="center")

        # Collect unique case IDs
        first_suite = next(iter(matrix.model_results.values()))
        for case in first_suite.results:
            row_items = [case.case_id]
            for m in model_names:
                m_case = next((c for c in matrix.model_results[m].results if c.case_id == case.case_id), None)
                if m_case:
                    icon = "[bold green]PASS[/bold green]" if m_case.passed else "[bold red]FAIL[/bold red]"
                else:
                    icon = "[dim]N/A[/dim]"
                row_items.append(icon)
            case_table.add_row(*row_items)

        console.print(case_table)
        console.print()
