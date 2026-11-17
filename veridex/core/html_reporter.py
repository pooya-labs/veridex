from __future__ import annotations

import json
from pathlib import Path
from typing import Union
from veridex.core.models import SuiteResult
from veridex import __version__


class HtmlReporter:
    """Generates an enterprise-grade standalone, interactive HTML dashboard report for evaluation runs."""

    @classmethod
    def generate(cls, result: SuiteResult) -> str:
        data_json = result.model_dump_json()
        pass_color = "#10b981" if result.pass_rate >= 0.8 else ("#f59e0b" if result.pass_rate >= 0.5 else "#f43f5e")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Veridex Report: {result.suite_name}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #07090e;
      --card-bg: rgba(16, 22, 35, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-border-hover: rgba(56, 189, 248, 0.35);
      --accent: #38bdf8;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --pass: #10b981;
      --pass-bg: rgba(16, 185, 129, 0.12);
      --fail: #f43f5e;
      --fail-bg: rgba(244, 63, 94, 0.12);
      --warn: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      padding: 2.5rem 1.5rem;
      background-image: 
        radial-gradient(circle at 10% 0%, rgba(56, 189, 248, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 90% 100%, rgba(129, 140, 248, 0.05) 0%, transparent 45%);
    }}
    code, pre, .mono {{ font-family: 'JetBrains Mono', monospace; }}
    .container {{ max-width: 1240px; margin: 0 auto; }}

    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .brand-icon {{
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #0284c7, #6366f1);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .brand-title {{
      font-size: 1.25rem;
      font-weight: 800;
      color: #fff;
    }}
    .badge {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 3px 8px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
    }}

    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1.25rem;
      margin-bottom: 2rem;
    }}
    @media (max-width: 900px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.25rem;
      backdrop-filter: blur(8px);
    }}
    .kpi-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
    }}
    .kpi-val {{
      font-size: 1.85rem;
      font-weight: 800;
    }}

    .toolbar {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .input-box {{
      background: #090e17;
      border: 1px solid var(--card-border);
      color: #fff;
      padding: 0.5rem 0.85rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-family: inherit;
      outline: none;
    }}
    .filter-tabs {{
      display: flex;
      gap: 4px;
      background: #090e17;
      padding: 3px;
      border-radius: 6px;
      border: 1px solid var(--card-border);
    }}
    .filter-pill {{
      padding: 0.35rem 0.75rem;
      font-size: 0.8rem;
      font-weight: 600;
      border-radius: 4px;
      cursor: pointer;
      color: var(--text-muted);
      border: none;
      background: transparent;
    }}
    .filter-pill.active {{
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }}

    .table-container {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }}
    th {{
      background: rgba(12, 16, 25, 0.95);
      padding: 0.85rem 1.25rem;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
      border-bottom: 1px solid var(--card-border);
    }}
    td {{
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--card-border);
      font-size: 0.88rem;
    }}
    tr:last-child td {{ border-bottom: none; }}
    .badge-status {{
      display: inline-flex;
      align-items: center;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
    }}
    .badge-pass {{ background: var(--pass-bg); color: var(--pass); border: 1px solid rgba(16, 185, 129, 0.25); }}
    .badge-fail {{ background: var(--fail-bg); color: var(--fail); border: 1px solid rgba(244, 63, 94, 0.25); }}

    /* Drawer */
    .drawer-overlay {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      z-index: 100;
    }}
    .drawer {{
      position: fixed;
      top: 0; right: 0; bottom: 0;
      width: 620px;
      max-width: 90vw;
      background: #0d121c;
      border-left: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      z-index: 101;
      padding: 2rem;
      gap: 1.5rem;
      overflow-y: auto;
    }}
    .code-box {{
      background: #07090e;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem;
      font-size: 0.82rem;
      overflow-x: auto;
      white-space: pre-wrap;
    }}
    .btn {{
      padding: 0.45rem 0.9rem;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--card-border);
      background: rgba(255, 255, 255, 0.05);
      color: #fff;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <div>
          <div class="brand-title">{result.suite_name}</div>
          <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 2px;">Provider: {result.provider} ({result.model}) • {result.timestamp}</div>
        </div>
      </div>
      <div>
        <span class="badge">Veridex v{__version__} Report</span>
      </div>
    </header>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Pass Rate</div>
        <div class="kpi-val" style="color: {pass_color};">{result.pass_rate * 100:.1f}%</div>
        <div style="font-size:0.8rem; color:var(--text-dim); margin-top:4px;">Threshold Target: 80%</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Tests Passed / Total</div>
        <div class="kpi-val">{result.passed_cases} / {result.total_cases}</div>
        <div style="font-size:0.8rem; color:var(--text-dim); margin-top:4px;">{result.failed_cases} failures</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Average Latency</div>
        <div class="kpi-val">{result.average_latency_ms:.1f}ms</div>
        <div style="font-size:0.8rem; color:var(--text-dim); margin-top:4px;">Asynchronous execution</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Inference Tokens & Cost</div>
        <div class="kpi-val">${result.total_cost_usd:.4f}</div>
        <div style="font-size:0.8rem; color:var(--text-dim); margin-top:4px;">{result.total_tokens} total tokens</div>
      </div>
    </div>

    <div class="toolbar">
      <input type="text" id="searchInput" class="input-box" placeholder="Search test cases..." oninput="renderTable()" style="width: 260px;">
      <div class="filter-tabs">
        <button class="filter-pill active" onclick="setFilter('all')">All ({result.total_cases})</button>
        <button class="filter-pill" onclick="setFilter('pass')">Passed ({result.passed_cases})</button>
        <button class="filter-pill" onclick="setFilter('fail')">Failed ({result.failed_cases})</button>
      </div>
    </div>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th style="width:90px;">Status</th>
            <th style="width:190px;">Case ID</th>
            <th>Name & Prompt</th>
            <th style="width:110px;">Latency</th>
            <th style="width:90px;">Tokens</th>
            <th style="width:120px;">Assertions</th>
            <th style="width:80px; text-align:center;">Action</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>

  <div class="drawer-overlay" id="overlay" onclick="closeDrawer()"></div>
  <div class="drawer" id="drawer" style="display:none;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <div id="drawerTitle" style="font-size:1.1rem; font-weight:700;">Case Details</div>
      <button class="btn" onclick="closeDrawer()">✕</button>
    </div>
    <div>
      <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700; margin-bottom:4px;">INPUT PROMPT</div>
      <div class="code-box" id="drawerPrompt"></div>
    </div>
    <div>
      <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700; margin-bottom:4px;">MODEL OUTPUT</div>
      <div class="code-box" id="drawerOutput"></div>
    </div>
    <div>
      <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700; margin-bottom:4px;">ASSERTION RESULTS</div>
      <div id="drawerAssertions" style="display:flex; flex-direction:column; gap:8px;"></div>
    </div>
  </div>

  <script>
    const data = {data_json};
    let currentFilter = 'all';

    function setFilter(f) {{
      currentFilter = f;
      document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      renderTable();
    }}

    function renderTable() {{
      const tbody = document.getElementById('tableBody');
      const q = (document.getElementById('searchInput').value || '').toLowerCase();
      tbody.innerHTML = '';

      const filtered = data.results.filter(c => {{
        if (currentFilter === 'pass' && !c.passed) return false;
        if (currentFilter === 'fail' && c.passed) return false;
        if (q && !c.case_id.toLowerCase().includes(q) && !c.case_name.toLowerCase().includes(q)) return false;
        return true;
      }});

      if (filtered.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:3rem; color:var(--text-dim);</td></tr>';
        return;
      }}

      filtered.forEach(c => {{
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => openDrawer(c);

        const badge = c.passed
          ? '<span class="badge-status badge-pass">✓ PASS</span>'
          : '<span class="badge-status badge-fail">✗ FAIL</span>';

        const passA = c.assertion_results.filter(a => a.passed).length;

        tr.innerHTML = `
          <td>${{badge}}</td>
          <td class="mono" style="color:var(--accent); font-weight:600;">${{c.case_id}}</td>
          <td>
            <div style="font-weight:600; color:#fff;">${{c.case_name}}</div>
            <div style="font-size:0.75rem; color:var(--text-dim); margin-top:2px;">${{c.input_prompt.substring(0, 70)}}...</div>
          </td>
          <td class="mono">${{c.latency_ms.toFixed(1)}}ms</td>
          <td class="mono">${{c.token_usage.total_tokens || 0}}</td>
          <td class="mono"><strong>${{passA}}</strong> / ${{c.assertion_results.length}}</td>
          <td style="text-align:center;"><button class="btn">View</button></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function openDrawer(c) {{
      document.getElementById('drawerTitle').innerText = c.case_name;
      document.getElementById('drawerPrompt').innerText = c.input_prompt;
      document.getElementById('drawerOutput').innerText = c.output;

      const aBox = document.getElementById('drawerAssertions');
      aBox.innerHTML = '';
      c.assertion_results.forEach(a => {{
        const el = document.createElement('div');
        el.style.background = '#090e17';
        el.style.border = `1px solid ${{a.passed ? 'rgba(16,185,129,0.25)' : 'rgba(244,63,94,0.3)'}}`;
        el.style.borderRadius = '6px';
        el.style.padding = '8px 12px';
        el.innerHTML = `
          <div style="display:flex; justify-content:space-between; font-weight:700; color:${{a.passed ? 'var(--pass)' : 'var(--fail)'}}; font-size:0.85rem;">
            <span>${{a.passed ? '✓' : '✗'}} [${{a.assertion_type}}] ${{a.name || ''}}</span>
            <span class="mono">score: ${{a.score}}</span>
          </div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:3px;">${{a.message}}</div>
        `;
        aBox.appendChild(el);
      }});

      document.getElementById('overlay').style.display = 'block';
      document.getElementById('drawer').style.display = 'flex';
    }}

    function closeDrawer() {{
      document.getElementById('overlay').style.display = 'none';
      document.getElementById('drawer').style.display = 'none';
    }}

    renderTable();
  </script>
</body>
</html>
"""
