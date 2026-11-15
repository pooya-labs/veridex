from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from veridex.core.models import SuiteResult


class RegressionDiff(BaseModel):
    baseline_id: str
    current_id: str
    pass_rate_delta: float
    latency_delta_ms: float
    cost_delta_usd: float
    regressions: List[str] = Field(default_factory=list)  # cases passed in baseline, failed in current
    improvements: List[str] = Field(default_factory=list)  # cases failed in baseline, passed in current
    unchanged_passed: List[str] = Field(default_factory=list)
    unchanged_failed: List[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        return SuiteComparator.to_markdown(self)


class SuiteComparator:
    """Compares two evaluation runs to detect performance regressions and improvements."""

    @classmethod
    def compare_files(cls, baseline_path: Union[str, Path], current_path: Union[str, Path]) -> RegressionDiff:
        with open(baseline_path, "r", encoding="utf-8") as f:
            base_data = json.load(f)
        with open(current_path, "r", encoding="utf-8") as f:
            curr_data = json.load(f)

        base_res = SuiteResult.model_validate(base_data)
        curr_res = SuiteResult.model_validate(curr_data)
        return cls.compare(base_res, curr_res)

    @classmethod
    def compare(cls, baseline: SuiteResult, current: SuiteResult) -> RegressionDiff:
        base_map = {r.case_id: r.passed for r in baseline.results}
        curr_map = {r.case_id: r.passed for r in current.results}

        regressions: list[str] = []
        improvements: list[str] = []
        unchanged_passed: list[str] = []
        unchanged_failed: list[str] = []

        all_ids = set(base_map.keys()).union(set(curr_map.keys()))

        for cid in sorted(all_ids):
            base_passed = base_map.get(cid, False)
            curr_passed = curr_map.get(cid, False)

            if base_passed and not curr_passed:
                regressions.append(cid)
            elif not base_passed and curr_passed:
                improvements.append(cid)
            elif curr_passed:
                unchanged_passed.append(cid)
            else:
                unchanged_failed.append(cid)

        pass_rate_delta = current.pass_rate - baseline.pass_rate
        latency_delta = current.average_latency_ms - baseline.average_latency_ms
        cost_delta = current.total_cost_usd - baseline.total_cost_usd

        return RegressionDiff(
            baseline_id=f"{baseline.suite_id} ({baseline.model})",
            current_id=f"{current.suite_id} ({current.model})",
            pass_rate_delta=round(pass_rate_delta, 4),
            latency_delta_ms=round(latency_delta, 2),
            cost_delta_usd=round(cost_delta, 6),
            regressions=regressions,
            improvements=improvements,
            unchanged_passed=unchanged_passed,
            unchanged_failed=unchanged_failed,
        )

    @classmethod
    def print_diff(cls, diff: RegressionDiff, console: Optional[Console] = None) -> None:
        console = console or Console()
        console.print()

        title = "[bold yellow]VERIDEX REGRESSION & BENCHMARK COMPARISON[/bold yellow]"
        console.print(Panel(title, expand=False, border_style="yellow"))

        table = Table(title="Delta Metrics", show_header=True)
        table.add_column("Metric", style="bold")
        table.add_column("Baseline", style="dim")
        table.add_column("Current")
        table.add_column("Delta", justify="right")

        # Pass rate
        rate_delta_str = f"{diff.pass_rate_delta * 100:+.1f}%"
        rate_style = "green" if diff.pass_rate_delta > 0 else "red" if diff.pass_rate_delta < 0 else "white"
        table.add_row("Pass Rate Delta", diff.baseline_id, diff.current_id, f"[{rate_style}]{rate_delta_str}[/{rate_style}]")

        # Latency
        lat_delta_str = f"{diff.latency_delta_ms:+.1f} ms"
        lat_style = "green" if diff.latency_delta_ms < 0 else "yellow" if diff.latency_delta_ms > 0 else "white"
        table.add_row("Latency Delta", "", "", f"[{lat_style}]{lat_delta_str}[/{lat_style}]")

        # Cost
        cost_delta_str = f"${diff.cost_delta_usd:+.4f}"
        cost_style = "green" if diff.cost_delta_usd <= 0 else "yellow"
        table.add_row("Cost Delta", "", "", f"[{cost_style}]{cost_delta_str}[/{cost_style}]")

        console.print(table)
        console.print()

        if diff.regressions:
            console.print(f"[bold red]⚠️ REGRESSIONS DETECTED ({len(diff.regressions)} cases broken!):[/bold red]")
            for reg in diff.regressions:
                console.print(f"  ❌ [red]{reg}[/red] (Passed in baseline, now FAILED)")
            console.print()

        if diff.improvements:
            console.print(f"[bold green]🎉 IMPROVEMENTS ({len(diff.improvements)} cases fixed!):[/bold green]")
            for imp in diff.improvements:
                console.print(f"  ✅ [green]{imp}[/green] (Failed in baseline, now PASSED)")
            console.print()

        if not diff.regressions and not diff.improvements:
            console.print("[dim]No changes in case pass/fail statuses between runs.[/dim]\n")

    @classmethod
    def to_markdown(cls, diff: RegressionDiff) -> str:
        """Render a GitHub-flavored Markdown regression report suitable for PR comments and CI summaries."""
        status_badge = "✅ **Passed — No Regressions**" if not diff.regressions else f"❌ **{len(diff.regressions)} Regressions Detected**"
        rate_arrow = "▲" if diff.pass_rate_delta > 0 else ("▼" if diff.pass_rate_delta < 0 else "—")
        lat_arrow = "▲" if diff.latency_delta_ms > 0 else ("▼" if diff.latency_delta_ms < 0 else "—")
        cost_arrow = "▲" if diff.cost_delta_usd > 0 else ("▼" if diff.cost_delta_usd < 0 else "—")

        md = [
            "## 🔍 Veridex LLM Evaluation & Regression Diff",
            f"**Status:** {status_badge}",
            "",
            "| Metric | Baseline | Current | Delta |",
            "| :--- | :--- | :--- | :---: |",
            f"| **Pass Rate** | `{diff.baseline_id}` | `{diff.current_id}` | **{rate_arrow} {diff.pass_rate_delta * 100:+.1f}%** |",
            f"| **Avg Latency** | — | — | **{lat_arrow} {diff.latency_delta_ms:+.1f} ms** |",
            f"| **Total Cost** | — | — | **{cost_arrow} ${diff.cost_delta_usd:+.4f}** |",
            "",
        ]

        if diff.regressions:
            md.extend([
                f"### ⚠️ Regressions ({len(diff.regressions)})",
                "> The following test cases previously PASSED in baseline but now FAILED in candidate:",
                "",
                "| Case ID | Baseline | Current | Diagnostic |",
                "| :--- | :---: | :---: | :--- |",
            ])
            for cid in diff.regressions:
                md.append(f"| `{cid}` | ✅ PASSED | ❌ FAILED | Assertion regression detected |")
            md.append("")

        if diff.improvements:
            md.extend([
                f"### 🎉 Improvements ({len(diff.improvements)})",
                "> The following test cases previously FAILED in baseline but now PASSED in candidate:",
                "",
                "| Case ID | Baseline | Current |",
                "| :--- | :---: | :---: |",
            ])
            for cid in diff.improvements:
                md.append(f"| `{cid}` | ❌ FAILED | ✅ PASSED |")
            md.append("")

        if not diff.regressions and not diff.improvements:
            md.extend([
                "> ✨ **Clean Diff:** Case pass/fail status is identical across both evaluation runs.",
                ""
            ])

        return "\n".join(md)
