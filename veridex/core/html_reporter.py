from __future__ import annotations

import json
from pathlib import Path
from typing import Union
from veridex.core.models import SuiteResult


class HtmlReporter:
    """Generates a standalone, interactive HTML dashboard report for evaluation runs."""

    @classmethod
    def generate(cls, result: SuiteResult) -> str:
        data_json = result.model_dump_json()
        pass_color = "#10b981" if result.pass_rate >= 0.8 else ("#f59e0b" if result.pass_rate >= 0.5 else "#ef4444")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Veridex Evaluation: {result.suite_name}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #111827;
      --border: rgba(255, 255, 255, 0.1);
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --cyan: #06b6d4;
      --green: #10b981;
      --red: #ef4444;
      --yellow: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 30px 20px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1080px; margin: 0 auto; }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 20px;
      margin-bottom: 30px;
    }}
    .logo {{ font-size: 1.4rem; font-weight: 800; color: #fff; letter-spacing: -0.02em; }}
    .badge {{ background: var(--cyan); color: #000; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; }}
    .meta-cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 30px;
    }}
    .meta-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
    }}
    .meta-title {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; }}
    .meta-value {{ font-size: 1.7rem; font-weight: 800; }}
    
    /* Filters */
    .filter-bar {{ display: flex; gap: 10px; margin-bottom: 24px; }}
    .filter-btn {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 18px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .filter-btn.active {{ background: rgba(6, 182, 212, 0.2); border-color: var(--cyan); color: var(--cyan); }}
    
    /* Case Item */
    .case-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      margin-bottom: 14px;
      overflow: hidden;
    }}
    .case-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      cursor: pointer;
      user-select: none;
    }}
    .case-title {{ display: flex; align-items: center; gap: 12px; font-weight: 600; font-size: 1.05rem; }}
    .st-pass {{ color: var(--green); font-weight: 800; }}
    .st-fail {{ color: var(--red); font-weight: 800; }}
    .case-body {{
      padding: 20px;
      border-top: 1px solid var(--border);
      background: #080b13;
      display: none;
      font-size: 0.9rem;
    }}
    .case-body.open {{ display: block; }}
    .field-title {{ color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 4px; font-weight: 700; }}
    .code-box {{
      background: #000;
      padding: 12px;
      border-radius: 6px;
      font-family: monospace;
      font-size: 0.85rem;
      white-space: pre-wrap;
      word-break: break-all;
      margin-bottom: 16px;
    }}
    .assertions-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }}
    .assertions-table th, .assertions-table td {{
      padding: 8px 12px;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo">VERIDEX <span style="font-weight:400; color:var(--text-muted);">| {result.suite_name}</span></div>
      <div class="badge">{result.provider} ({result.model})</div>
    </header>

    <div class="meta-cards">
      <div class="meta-card">
        <div class="meta-title">Pass Rate</div>
        <div class="meta-value" style="color:{pass_color};">{result.pass_rate * 100:.1f}%</div>
        <div style="font-size:0.8rem; color:var(--text-muted);">{result.passed_cases} passed / {result.total_cases} total</div>
      </div>
      <div class="meta-card">
        <div class="meta-title">Avg Latency</div>
        <div class="meta-value">{result.average_latency_ms:.1f} <span style="font-size:1rem; font-weight:400;">ms</span></div>
      </div>
      <div class="meta-card">
        <div class="meta-title">Total Tokens</div>
        <div class="meta-value">{result.total_tokens:,}</div>
      </div>
      <div class="meta-card">
        <div class="meta-title">Estimated Cost</div>
        <div class="meta-value">${result.total_cost_usd:.4f}</div>
      </div>
    </div>

    <div class="filter-bar">
      <button class="filter-btn active" onclick="filterCases('all')">All Cases ({result.total_cases})</button>
      <button class="filter-btn" onclick="filterCases('passed')">Passed ({result.passed_cases})</button>
      <button class="filter-btn" onclick="filterCases('failed')">Failed ({result.failed_cases})</button>
    </div>

    <div id="cases-container"></div>
  </div>

  <script>
    const data = {data_json};

    function renderCases(filter) {{
      const container = document.getElementById('cases-container');
      container.innerHTML = '';

      data.results.forEach((c, idx) => {{
        if (filter === 'passed' && !c.passed) return;
        if (filter === 'failed' && c.passed) return;

        const card = document.createElement('div');
        card.className = 'case-card';

        const statusClass = c.passed ? 'st-pass' : 'st-fail';
        const statusText = c.passed ? '✓ PASS' : '✗ FAIL';
        const passedA = c.assertion_results.filter(a => a.passed).length;
        const totalA = c.assertion_results.length;

        card.innerHTML = `
          <div class="case-header" onclick="toggleCase(${{idx}})">
            <div class="case-title">
              <span class="${{statusClass}}">${{statusText}}</span>
              <span>${{c.case_name}}</span>
              <span style="font-size:0.8rem; color:var(--text-muted); font-family:monospace;">(${{c.case_id}})</span>
            </div>
            <div style="color:var(--text-muted); font-size:0.85rem;">
              ${{c.latency_ms.toFixed(1)}}ms | ${{passedA}}/${{totalA}} assertions
            </div>
          </div>
          <div class="case-body" id="body-${{idx}}">
            <div class="field-title">Prompt</div>
            <div class="code-box">${{c.input_prompt}}</div>

            <div class="field-title">Completion Output</div>
            <div class="code-box">${{c.output || '<empty>'}}</div>

            <div class="field-title">Assertions Breakdown</div>
            <table class="assertions-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Type</th>
                  <th>Diagnostic Message</th>
                </tr>
              </thead>
              <tbody>
                ${{c.assertion_results.map(a => `
                  <tr>
                    <td style="color:${{a.passed ? 'var(--green)' : 'var(--red)'}}; font-weight:bold;">
                      ${{a.passed ? 'PASS' : 'FAIL'}}
                    </td>
                    <td style="font-family:monospace;">${{a.assertion_type}}</td>
                    <td>${{a.message}}</td>
                  </tr>
                `).join('')}}
              </tbody>
            </table>
          </div>
        `;
        container.appendChild(card);
      }});
    }}

    function toggleCase(idx) {{
      const b = document.getElementById('body-' + idx);
      b.classList.toggle('open');
    }}

    function filterCases(filter) {{
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      renderCases(filter);
    }}

    renderCases('all');
  </script>
</body>
</html>
"""

    @classmethod
    def export(cls, result: SuiteResult, output_path: Union[str, Path]) -> None:
        html = cls.generate(result)
        path = Path(output_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
