from __future__ import annotations

import asyncio
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional

from veridex.core.runner import TestRunner
from veridex.core.matrix import MatrixRunner
from veridex.loaders.yaml_loader import SuiteLoader
from veridex.providers.mock import MockProvider
from veridex import __version__

logger = logging.getLogger("veridex.server")


def _get_web_dashboard_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Veridex Live Evaluation Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #111827;
      --card-border: #1f2937;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.2);
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --pass: #10b981;
      --pass-bg: rgba(16, 185, 129, 0.12);
      --fail: #ef4444;
      --fail-bg: rgba(239, 68, 68, 0.12);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 2rem;
      border-bottom: 1px solid var(--card-border);
      background: rgba(17, 24, 39, 0.8);
      backdrop-filter: blur(12px);
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 800;
      font-size: 1.25rem;
      color: #fff;
    }}
    .logo span {{ color: var(--accent); }}
    .badge {{
      background: var(--accent-glow);
      color: var(--accent);
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }}
    main {{
      flex: 1;
      padding: 2rem;
      max-width: 1400px;
      margin: 0 auto;
      width: 100%;
    }}
    .control-panel {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 2rem;
      display: flex;
      flex-wrap: wrap;
      gap: 1.25rem;
      align-items: flex-end;
    }}
    .input-group {{
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      flex: 1;
      min-width: 260px;
    }}
    label {{
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
    }}
    input, select {{
      background: #0d131f;
      border: 1px solid var(--card-border);
      color: #fff;
      padding: 0.65rem 0.9rem;
      border-radius: 8px;
      font-family: inherit;
      font-size: 0.9rem;
      outline: none;
      transition: border 0.2s;
    }}
    input:focus, select:focus {{
      border-color: var(--accent);
    }}
    .btn {{
      background: linear-gradient(135deg, #0284c7, #2563eb);
      color: #fff;
      padding: 0.7rem 1.4rem;
      border-radius: 8px;
      border: none;
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s;
    }}
    .btn:hover {{
      transform: translateY(-1px);
      box-shadow: 0 4px 14px var(--accent-glow);
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1.2rem;
    }}
    .stat-label {{
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.4rem;
    }}
    .stat-val {{
      font-size: 1.7rem;
      font-weight: 800;
    }}
    .results-table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
    }}
    th, td {{
      padding: 1rem 1.25rem;
      text-align: left;
      border-bottom: 1px solid var(--card-border);
    }}
    th {{
      background: #0f172a;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }}
    tr:last-child td {{ border-bottom: none; }}
    .tag-pass {{
      background: var(--pass-bg);
      color: var(--pass);
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.8rem;
    }}
    .tag-fail {{
      background: var(--fail-bg);
      color: var(--fail);
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.8rem;
    }}
    .mono {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="logo">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      Veridex <span>Studio</span>
      <span class="badge">v{__version__}</span>
    </div>
    <div style="font-size: 0.85rem; color: var(--text-muted)">
      Live AI Evaluation & Regression Server
    </div>
  </header>

  <main>
    <div class="control-panel">
      <div class="input-group">
        <label>Preset Suite or Custom URL / Path</label>
        <select id="suiteSelect" onchange="onSuiteSelect(this.value)">
          <option value="examples/01_structured_extraction/suite.yaml">01: Structured Extraction Suite</option>
          <option value="examples/02_rag_hallucination/suite.yaml">02: RAG Groundedness Suite</option>
          <option value="examples/03_agent_safety/suite.yaml">03: Agent Safety & PII Suite</option>
          <option value="examples/04_rag_faithfulness/suite.yaml">04: RAG Faithfulness & Relevance Suite</option>
          <option value="examples/05_model_matrix/suite.yaml">05: Multi-Model Benchmark Matrix</option>
          <option value="custom">Custom URL or local path...</option>
        </select>
        <input type="text" id="suiteCustom" placeholder="https://raw.githubusercontent.com/.../suite.yaml" style="display:none; margin-top:0.4rem;">
      </div>
      <div class="input-group" style="flex:0.6; min-width: 180px;">
        <label>Execution Mode</label>
        <select id="simMode">
          <option value="true">Simulate Success (Zero-Cost)</option>
          <option value="false">Live Execution</option>
        </select>
      </div>
      <div>
        <button class="btn" id="runBtn" onclick="executeSuite()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          Run Evaluation
        </button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Pass Rate</div>
        <div class="stat-val" id="statPassRate" style="color: var(--accent);">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Passed / Total</div>
        <div class="stat-val" id="statRatio">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Latency</div>
        <div class="stat-val" id="statLatency">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Cost</div>
        <div class="stat-val" id="statCost">--</div>
      </div>
    </div>

    <table class="results-table">
      <thead>
        <tr>
          <th>Status</th>
          <th>Case ID</th>
          <th>Name</th>
          <th>Latency</th>
          <th>Tokens</th>
          <th>Assertions</th>
          <th>Diagnostics</th>
        </tr>
      </thead>
      <tbody id="resultsBody">
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 3rem;">
            Click <strong>Run Evaluation</strong> above to execute tests in real-time.
          </td>
        </tr>
      </tbody>
    </table>
  </main>

  <script>
    function onSuiteSelect(val) {{
      const customInput = document.getElementById('suiteCustom');
      customInput.style.display = val === 'custom' ? 'block' : 'none';
    }}

    async function executeSuite() {{
      const runBtn = document.getElementById('runBtn');
      const select = document.getElementById('suiteSelect');
      const custom = document.getElementById('suiteCustom');
      const simMode = document.getElementById('simMode').value === 'true';

      const suitePath = select.value === 'custom' ? custom.value.trim() : select.value;
      if (!suitePath) {{
        alert('Please select or specify a test suite.');
        return;
      }}

      runBtn.disabled = true;
      runBtn.innerText = 'Running...';

      try {{
        const resp = await fetch('/api/run', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ suite: suitePath, simulate_success: simMode }})
        }});

        if (!resp.ok) {{
          const errData = await resp.json();
          alert('Evaluation error: ' + (errData.error || resp.statusText));
          return;
        }}

        const data = await resp.json();
        renderResults(data);
      }} catch (e) {{
        alert('Network or server error: ' + e);
      }} finally {{
        runBtn.disabled = false;
        runBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Run Evaluation';
      }}
    }}

    function renderResults(data) {{
      const passRate = (data.pass_rate * 100).toFixed(1) + '%';
      const statPassRate = document.getElementById('statPassRate');
      statPassRate.innerText = passRate;
      statPassRate.style.color = data.pass_rate >= 0.8 ? 'var(--pass)' : 'var(--fail)';

      document.getElementById('statRatio').innerText = `${{data.passed_cases}} / ${{data.total_cases}}`;
      document.getElementById('statLatency').innerText = `${{data.average_latency_ms.toFixed(1)}}ms`;
      document.getElementById('statCost').innerText = `$${{data.total_cost_usd.toFixed(4)}}`;

      const tbody = document.getElementById('resultsBody');
      tbody.innerHTML = '';

      data.results.forEach(c => {{
        const tr = document.createElement('tr');
        const badge = c.passed 
          ? '<span class="tag-pass">PASS</span>'
          : '<span class="tag-fail">FAIL</span>';

        const failedMsgs = c.assertions
          .filter(a => !a.passed)
          .map(a => `✗ [${{a.assertion_type}}] ${{a.message}}`)
          .join('<br>');

        tr.innerHTML = `
          <td>${{badge}}</td>
          <td class="mono">${{c.case_id}}</td>
          <td style="font-weight: 600;">${{c.name}}</td>
          <td class="mono">${{c.latency_ms.toFixed(1)}}ms</td>
          <td class="mono">${{c.token_usage.total_tokens || 0}}</td>
          <td class="mono">${{c.assertions.filter(a => a.passed).length}} / ${{c.assertions.length}}</td>
          <td style="color: ${{c.passed ? 'var(--text-muted)' : 'var(--fail)'}}; font-size: 0.85rem;">
            ${{failedMsgs || 'All assertions passed.'}}
          </td>
        `;
        tbody.appendChild(tr);
      }});
    }}
  </script>
</body>
</html>"""


class VeridexStudioHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            html = _get_web_dashboard_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/api/status":
            resp = json.dumps({"status": "ok", "version": __version__})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/run":
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
                suite_source = payload.get("suite", "examples/01_structured_extraction/suite.yaml")
                sim_success = payload.get("simulate_success", False)

                suite = SuiteLoader.load_from_source(suite_source)
                runner = TestRunner()
                if sim_success and suite.provider == "mock":
                    runner.provider = MockProvider(model=suite.model or "mock-model", simulate_success=True)

                result = asyncio.run(runner.run_suite(suite))
                result_json = result.model_dump_json()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(result_json.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(result_json.encode("utf-8"))
            except Exception as e:
                err = json.dumps({"error": str(e)})
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(err.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_studio_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = HTTPServer((host, port), VeridexStudioHandler)
    print(f"\n⚡ Veridex Studio running at http://{host}:{port}/")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Veridex Studio...")
        server.server_close()
