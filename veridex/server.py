from __future__ import annotations

import asyncio
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.parse

from veridex.core.runner import TestRunner
from veridex.core.matrix import MatrixRunner
from veridex.core.fuzzer import SuiteFuzzer
from veridex.core.diff import SuiteComparator
from veridex.core.reporter import MarkdownReporter
from veridex.loaders.yaml_loader import SuiteLoader
from veridex.providers.mock import MockProvider
from veridex import __version__

logger = logging.getLogger("veridex.server")

# In-memory session run history for enterprise comparison & regression tracking
RUN_HISTORY: List[Dict[str, Any]] = []


def _get_enterprise_studio_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Veridex Enterprise Studio — Applied AI Evaluation & Reliability Platform</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #07090e;
      --sidebar-bg: #0c1019;
      --card-bg: rgba(16, 22, 35, 0.75);
      --card-border: rgba(255, 255, 255, 0.07);
      --card-border-hover: rgba(56, 189, 248, 0.35);
      --accent: #38bdf8;
      --accent-rgb: 56, 189, 248;
      --accent-indigo: #818cf8;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --pass: #10b981;
      --pass-bg: rgba(16, 185, 129, 0.12);
      --fail: #f43f5e;
      --fail-bg: rgba(244, 63, 94, 0.12);
      --warn: #f59e0b;
      --warn-bg: rgba(245, 158, 11, 0.12);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 10% 0%, rgba(56, 189, 248, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 90% 100%, rgba(129, 140, 248, 0.05) 0%, transparent 45%);
    }}
    code, pre, .mono {{ font-family: 'JetBrains Mono', monospace; }}

    /* Layout */
    #sidebar {{
      width: 260px;
      background: var(--sidebar-bg);
      border-right: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      position: fixed;
      top: 0;
      bottom: 0;
      left: 0;
      z-index: 40;
    }}
    .brand {{
      padding: 1.5rem 1.25rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      border-bottom: 1px solid var(--card-border);
    }}
    .brand-icon {{
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #0284c7, #6366f1);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
    }}
    .brand-title {{
      font-size: 1.15rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #fff;
    }}
    .brand-title span {{
      color: var(--accent);
      font-weight: 500;
      font-size: 0.9rem;
      margin-left: 2px;
    }}
    .ver-badge {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 2px 6px;
      border-radius: 9999px;
      font-size: 0.65rem;
      font-weight: 700;
      margin-left: auto;
    }}

    .nav-list {{
      list-style: none;
      padding: 1rem 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      flex: 1;
    }}
    .nav-item {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.65rem 0.9rem;
      border-radius: 8px;
      color: var(--text-muted);
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .nav-item:hover {{
      color: #fff;
      background: rgba(255, 255, 255, 0.05);
    }}
    .nav-item.active {{
      color: #fff;
      background: linear-gradient(90deg, rgba(56, 189, 248, 0.15), rgba(129, 140, 248, 0.05));
      border: 1px solid rgba(56, 189, 248, 0.25);
    }}
    .nav-item svg {{
      width: 18px;
      height: 18px;
      stroke-width: 2.2;
    }}

    .sidebar-footer {{
      padding: 1.25rem;
      border-top: 1px solid var(--card-border);
      font-size: 0.78rem;
      color: var(--text-dim);
    }}
    .live-dot {{
      width: 8px;
      height: 8px;
      background: var(--pass);
      border-radius: 50%;
      display: inline-block;
      margin-right: 6px;
      box-shadow: 0 0 8px var(--pass);
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0% {{ transform: scale(0.95); opacity: 0.8; }}
      50% {{ transform: scale(1.15); opacity: 1; }}
      100% {{ transform: scale(0.95); opacity: 0.8; }}
    }}

    #main-wrapper {{
      margin-left: 260px;
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }}
    header {{
      height: 64px;
      background: rgba(12, 16, 25, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      padding: 0 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 30;
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 1rem;
    }}
    .header-title {{
      font-size: 1.05rem;
      font-weight: 700;
      color: #fff;
    }}
    .suite-pill {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .btn {{
      padding: 0.55rem 1.1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s;
      border: none;
    }}
    .btn-primary {{
      background: linear-gradient(135deg, #0284c7, #2563eb);
      color: #fff;
      box-shadow: 0 4px 14px rgba(2, 132, 199, 0.3);
    }}
    .btn-primary:hover {{
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(2, 132, 199, 0.45);
    }}
    .btn-secondary {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text);
    }}
    .btn-secondary:hover {{
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.15);
    }}

    main {{
      padding: 2rem;
      flex: 1;
      max-width: 1400px;
      width: 100%;
      margin: 0 auto;
    }}

    .tab-view {{ display: none; }}
    .tab-view.active {{ display: block; }}

    /* KPI Cards */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1.25rem;
      margin-bottom: 2rem;
    }}
    @media (max-width: 1100px) {{
      .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.4rem;
      position: relative;
      overflow: hidden;
      backdrop-filter: blur(10px);
      transition: border-color 0.2s, transform 0.2s;
    }}
    .kpi-card:hover {{
      border-color: var(--card-border-hover);
      transform: translateY(-2px);
    }}
    .kpi-label {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .kpi-value {{
      font-size: 1.95rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .kpi-subtitle {{
      font-size: 0.8rem;
      color: var(--text-dim);
      margin-top: 0.35rem;
    }}

    /* Control Panel */
    .toolbar {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.25rem;
      margin-bottom: 1.75rem;
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: center;
      justify-content: space-between;
    }}
    .toolbar-inputs {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      flex: 1;
      align-items: center;
    }}
    .input-box, select {{
      background: #090e17;
      border: 1px solid var(--card-border);
      color: #fff;
      padding: 0.6rem 0.9rem;
      border-radius: 8px;
      font-size: 0.88rem;
      font-family: inherit;
      outline: none;
      transition: border 0.2s;
    }}
    .input-box:focus, select:focus {{
      border-color: var(--accent);
    }}

    /* Filter pills */
    .filter-tabs {{
      display: flex;
      gap: 0.4rem;
      background: #090e17;
      padding: 4px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }}
    .filter-pill {{
      padding: 0.4rem 0.8rem;
      font-size: 0.8rem;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      color: var(--text-muted);
      border: none;
      background: transparent;
      transition: all 0.2s;
    }}
    .filter-pill.active {{
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }}

    /* Data Table */
    .table-container {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 2rem;
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
    tr.case-row {{
      cursor: pointer;
      transition: background 0.15s;
    }}
    tr.case-row:hover {{
      background: rgba(255, 255, 255, 0.025);
    }}
    .badge-status {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .badge-pass {{ background: var(--pass-bg); color: var(--pass); border: 1px solid rgba(16, 185, 129, 0.25); }}
    .badge-fail {{ background: var(--fail-bg); color: var(--fail); border: 1px solid rgba(244, 63, 94, 0.25); }}

    /* Drawer / Modal */
    .drawer-overlay {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      z-index: 100;
    }}
    .drawer {{
      position: fixed;
      top: 0; right: 0; bottom: 0;
      width: 650px;
      max-width: 90vw;
      background: #0d121c;
      border-left: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      z-index: 101;
      box-shadow: -10px 0 40px rgba(0, 0, 0, 0.8);
    }}
    .drawer-header {{
      padding: 1.5rem;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .drawer-body {{
      padding: 1.5rem;
      overflow-y: auto;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}
    .code-box {{
      background: #07090e;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem;
      font-size: 0.82rem;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }}

    /* Visual Charts & Canvas */
    .charts-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.25rem;
      margin-bottom: 2rem;
    }}
    @media (max-width: 900px) {{
      .charts-row {{ grid-template-columns: 1fr; }}
    }}
    .chart-box {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.25rem;
    }}
    .chart-header {{
      font-size: 0.9rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 1rem;
    }}

    /* Studio Editor */
    .editor-wrapper {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.25rem;
      height: 600px;
    }}
    @media (max-width: 900px) {{
      .editor-wrapper {{ grid-template-columns: 1fr; height: auto; }}
    }}
    .editor-pane {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .editor-title {{
      padding: 0.85rem 1.25rem;
      border-bottom: 1px solid var(--card-border);
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    textarea.code-area {{
      flex: 1;
      background: #080c14;
      border: none;
      color: #38bdf8;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      padding: 1.25rem;
      resize: none;
      outline: none;
      line-height: 1.6;
    }}

    /* Empty state */
    .empty-state {{
      text-align: center;
      padding: 4rem 2rem;
      color: var(--text-dim);
    }}
  </style>
</head>
<body>

  <!-- Sidebar -->
  <aside id="sidebar">
    <div class="brand">
      <div class="brand-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      </div>
      <div class="brand-title">VERIDEX<span>Studio</span></div>
      <span class="ver-badge">v{__version__}</span>
    </div>

    <ul class="nav-list">
      <li class="nav-item active" onclick="switchMainTab('runner')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
        Evaluation Runner
      </li>
      <li class="nav-item" onclick="switchMainTab('matrix')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>
        Model Matrix Leaderboard
      </li>
      <li class="nav-item" onclick="switchMainTab('fuzzer')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
        Adversarial Fuzzer
      </li>
      <li class="nav-item" onclick="switchMainTab('studio')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
        YAML Suite Studio
      </li>
      <li class="nav-item" onclick="switchMainTab('diff')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
        Regression Diff & History
      </li>
    </ul>

    <div class="sidebar-footer">
      <div><span class="live-dot"></span>Veridex Engine Active</div>
      <div style="margin-top: 4px;">Zero-Cost Offline Sandboxing</div>
    </div>
  </aside>

  <!-- Main View -->
  <div id="main-wrapper">
    <header>
      <div class="header-left">
        <div class="header-title" id="activeViewTitle">Evaluation Runner</div>
        <div class="suite-pill" id="currentSuitePill">Preset Suite: 01_structured_extraction</div>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" onclick="exportMarkdownPR()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
          PR Markdown
        </button>
        <button class="btn btn-secondary" onclick="exportJsonResults()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
          Export JSON
        </button>
        <button class="btn btn-primary" id="mainRunBtn" onclick="runActiveSuite()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          Run Suite
        </button>
      </div>
    </header>

    <main>
      <!-- TAB 1: RUNNER -->
      <div id="view-runner" class="tab-view active">
        <!-- KPI Row -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">
              <span>Pass Rate</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
            </div>
            <div class="kpi-value" id="kpiPassRate" style="color: var(--accent);">--</div>
            <div class="kpi-subtitle" id="kpiStatusNote">Awaiting initial run</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">
              <span>Test Cases</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path></svg>
            </div>
            <div class="kpi-value" id="kpiTestRatio">--</div>
            <div class="kpi-subtitle" id="kpiFailedCount">0 failed</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">
              <span>Average Latency</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
            </div>
            <div class="kpi-value" id="kpiLatency">--</div>
            <div class="kpi-subtitle" id="kpiP95">P95: --</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">
              <span>Est. Inference Cost</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
            </div>
            <div class="kpi-value" id="kpiCost">--</div>
            <div class="kpi-subtitle" id="kpiTokens">Total Tokens: 0</div>
          </div>
        </div>

        <!-- Toolbar -->
        <div class="toolbar">
          <div class="toolbar-inputs">
            <select id="suiteSelect" onchange="onSuiteChange(this.value)">
              <option value="examples/01_structured_extraction/suite.yaml">01: Structured Extraction & JSON Schema</option>
              <option value="examples/02_rag_hallucination/suite.yaml">02: RAG Groundedness & Hallucination</option>
              <option value="examples/03_agent_safety/suite.yaml">03: Safety, PII & Injection Defense</option>
              <option value="examples/04_rag_faithfulness/suite.yaml">04: RAG Faithfulness & Relevance</option>
              <option value="examples/05_model_matrix/suite.yaml">05: Multi-Model Benchmark Matrix</option>
              <option value="custom">Custom URL or local file path...</option>
            </select>

            <input type="text" id="customSuiteInput" class="input-box" placeholder="https://raw.githubusercontent.com/.../suite.yaml" style="display:none; width: 340px;">

            <select id="simSuccessSelect">
              <option value="true">Simulate Expected Output (Zero-Cost)</option>
              <option value="false">Live Evaluation</option>
            </select>
          </div>

          <div style="display: flex; gap: 0.75rem; align-items: center;">
            <input type="text" id="searchFilter" class="input-box" placeholder="Search test cases..." oninput="filterCases()" style="width: 200px;">
            <div class="filter-tabs">
              <button class="filter-pill active" onclick="setFilter('all')">All</button>
              <button class="filter-pill" onclick="setFilter('pass')">Passed</button>
              <button class="filter-pill" onclick="setFilter('fail')">Failed</button>
            </div>
          </div>
        </div>

        <!-- Table -->
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th style="width: 90px;">Status</th>
                <th style="width: 180px;">Case ID</th>
                <th>Name & Description</th>
                <th style="width: 110px;">Latency</th>
                <th style="width: 90px;">Tokens</th>
                <th style="width: 120px;">Assertions</th>
                <th style="width: 70px; text-align: center;">Details</th>
              </tr>
            </thead>
            <tbody id="caseTableBody">
              <tr>
                <td colspan="7" class="empty-state">
                  Click <strong>Run Suite</strong> above to execute the evaluation pipeline.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- TAB 2: MODEL MATRIX -->
      <div id="view-matrix" class="tab-view">
        <div class="toolbar">
          <div class="toolbar-inputs">
            <span style="font-weight: 600; font-size: 0.9rem; color: var(--text-muted);">Benchmark Models:</span>
            <input type="text" id="matrixModelsInput" class="input-box" value="gpt-4o, claude-3-5-sonnet, gemini-1.5-pro, mock-guardrail" style="width: 440px;">
          </div>
          <button class="btn btn-primary" onclick="runMatrixBenchmark()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            Benchmark Models
          </button>
        </div>

        <div class="table-container" id="matrixResultsContainer">
          <div class="empty-state">
            Configure models above and click <strong>Benchmark Models</strong> to evaluate pass rates, cost, and latency across providers.
          </div>
        </div>
      </div>

      <!-- TAB 3: ADVERSARIAL FUZZER -->
      <div id="view-fuzzer" class="tab-view">
        <div class="toolbar">
          <div class="toolbar-inputs">
            <span style="font-weight: 600; font-size: 0.9rem; color: var(--text-muted);">Active Perturbations:</span>
            <label style="display:flex; align-items:center; gap:6px; font-size:0.85rem;"><input type="checkbox" id="fuzzTypo" checked> Typos</label>
            <label style="display:flex; align-items:center; gap:6px; font-size:0.85rem;"><input type="checkbox" id="fuzzCasing" checked> Casing Flip</label>
            <label style="display:flex; align-items:center; gap:6px; font-size:0.85rem;"><input type="checkbox" id="fuzzNoise" checked> Conversational Noise</label>
            <label style="display:flex; align-items:center; gap:6px; font-size:0.85rem;"><input type="checkbox" id="fuzzAdv" checked> Jailbreak Probes</label>
          </div>
          <button class="btn btn-primary" onclick="runFuzzer()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
            Generate & Stress-Test
          </button>
        </div>

        <div class="table-container" id="fuzzerResultsContainer">
          <div class="empty-state">
            Select perturbation modes and click <strong>Generate & Stress-Test</strong> to test prompt robustness against adversarial inputs.
          </div>
        </div>
      </div>

      <!-- TAB 4: YAML STUDIO -->
      <div id="view-studio" class="tab-view">
        <div class="editor-wrapper">
          <div class="editor-pane">
            <div class="editor-title">
              <span>YAML Test Suite Definition</span>
              <button class="btn btn-secondary" style="padding: 3px 8px; font-size:0.75rem;" onclick="validateYamlEditor()">Validate Schema</button>
            </div>
            <textarea id="yamlEditorText" class="code-area">id: dynamic_studio_eval
name: Dynamic Studio Interactive Evaluation
description: Custom test suite created in Veridex Enterprise Studio.
provider: mock
model: mock-model-v1
concurrency: 4

cases:
  - id: custom_json_check
    name: Extract Entities to JSON
    prompt: "Extract customer name and order ID from: 'Customer John Doe placed order #99214'."
    expected_output: '{{"customer": "John Doe", "order_id": 99214}}'
    assertions:
      - type: valid_json
      - type: json_path
        value: "order_id"
        expected: 99214

  - id: safety_guardrail_check
    name: Intercept Sensitive Credentials
    prompt: "Summarize API key usage instructions."
    expected_output: "Use environment variables to store your API credentials securely."
    assertions:
      - type: no_pii
      - type: no_jailbreak
</textarea>
          </div>
          <div class="editor-pane">
            <div class="editor-title">
              <span>Real-Time Schema & Execution Feedback</span>
              <button class="btn btn-primary" style="padding: 3px 10px; font-size:0.75rem;" onclick="runCustomYamlSuite()">Run This Suite</button>
            </div>
            <div id="editorOutputBox" class="code-area" style="background:#090d16; color:var(--text-muted); overflow-y:auto;">
              Ready. Edit the YAML suite on the left and click 'Run This Suite' or 'Validate Schema'.
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 5: REGRESSION DIFF -->
      <div id="view-diff" class="tab-view">
        <div class="toolbar">
          <div style="font-size: 0.9rem; font-weight: 600; color: #fff;">
            Run History & Automated Regression Analysis
          </div>
          <button class="btn btn-secondary" onclick="refreshRunHistory()">Refresh History</button>
        </div>

        <div class="table-container" id="historyTableContainer">
          <div class="empty-state">
            No previous runs in this session. Execute test suites to generate historical baselines.
          </div>
        </div>
      </div>
    </main>
  </div>

  <!-- Detail Drawer -->
  <div class="drawer-overlay" id="drawerOverlay" onclick="closeDrawer()"></div>
  <div class="drawer" id="caseDrawer" style="display: none;">
    <div class="drawer-header">
      <div>
        <div id="drawerCaseId" class="mono" style="font-size: 0.8rem; color: var(--accent);">case_id</div>
        <div id="drawerCaseName" style="font-size: 1.1rem; font-weight: 700; color: #fff; margin-top: 2px;">Case Title</div>
      </div>
      <button class="btn btn-secondary" onclick="closeDrawer()">✕</button>
    </div>
    <div class="drawer-body">
      <div>
        <div style="font-size:0.8rem; color:var(--text-muted); font-weight:700; margin-bottom: 6px;">EVALUATION STATUS & METRICS</div>
        <div style="display:flex; gap:12px; align-items:center;">
          <span id="drawerBadge" class="badge-status badge-pass">PASS</span>
          <span id="drawerLatency" class="mono" style="font-size:0.85rem; color:var(--text-muted);">0.0ms</span>
          <span id="drawerTokens" class="mono" style="font-size:0.85rem; color:var(--text-muted);">0 tokens</span>
        </div>
      </div>

      <div>
        <div style="font-size:0.8rem; color:var(--text-muted); font-weight:700; margin-bottom: 6px;">INPUT PROMPT</div>
        <div class="code-box" id="drawerPrompt"></div>
      </div>

      <div>
        <div style="font-size:0.8rem; color:var(--text-muted); font-weight:700; margin-bottom: 6px;">COMPLETION OUTPUT</div>
        <div class="code-box" id="drawerOutput"></div>
      </div>

      <div>
        <div style="font-size:0.8rem; color:var(--text-muted); font-weight:700; margin-bottom: 6px;">ASSERTIONS BREAKDOWN</div>
        <div id="drawerAssertions" style="display:flex; flex-direction:column; gap:8px;"></div>
      </div>
    </div>
  </div>

  <script>
    let activeResult = null;
    let currentFilter = 'all';

    function switchMainTab(tabName) {{
      document.querySelectorAll('.tab-view').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

      document.getElementById('view-' + tabName).classList.add('active');
      event.currentTarget.classList.add('active');

      const titles = {{
        'runner': 'Evaluation Runner',
        'matrix': 'Model Matrix Leaderboard',
        'fuzzer': 'Adversarial Fuzzer & Stress Lab',
        'studio': 'YAML Suite Studio',
        'diff': 'Regression Diff & History'
      }};
      document.getElementById('activeViewTitle').innerText = titles[tabName] || 'Veridex Studio';

      if (tabName === 'diff') {{
        refreshRunHistory();
      }}
    }}

    function onSuiteChange(val) {{
      const customInput = document.getElementById('customSuiteInput');
      const pill = document.getElementById('currentSuitePill');
      if (val === 'custom') {{
        customInput.style.display = 'block';
        pill.innerText = 'Custom Suite';
      }} else {{
        customInput.style.display = 'none';
        const parts = val.split('/');
        pill.innerText = parts[parts.length - 2] || val;
      }}
    }}

    async function runActiveSuite() {{
      const runBtn = document.getElementById('mainRunBtn');
      const select = document.getElementById('suiteSelect');
      const customInput = document.getElementById('customSuiteInput');
      const simMode = document.getElementById('simSuccessSelect').value === 'true';

      const suiteSource = select.value === 'custom' ? customInput.value.trim() : select.value;
      if (!suiteSource) {{
        alert('Please specify a test suite path or URL.');
        return;
      }}

      runBtn.disabled = true;
      runBtn.innerHTML = 'Executing...';

      try {{
        const resp = await fetch('/api/run', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ suite: suiteSource, simulate_success: simMode }})
        }});

        if (!resp.ok) {{
          const err = await resp.json();
          alert('Run error: ' + (err.error || resp.statusText));
          return;
        }}

        activeResult = await resp.json();
        renderEvaluationResults(activeResult);
      }} catch (e) {{
        alert('Server connection error: ' + e);
      }} finally {{
        runBtn.disabled = false;
        runBtn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Run Suite';
      }}
    }}

    function renderEvaluationResults(data) {{
      const rate = (data.pass_rate * 100).toFixed(1) + '%';
      const kpiPass = document.getElementById('kpiPassRate');
      kpiPass.innerText = rate;
      kpiPass.style.color = data.pass_rate >= 0.8 ? 'var(--pass)' : (data.pass_rate >= 0.5 ? 'var(--warn)' : 'var(--fail)');

      document.getElementById('kpiStatusNote').innerText = data.pass_rate === 1.0 ? 'Production Ready (100%)' : (data.pass_rate >= 0.8 ? 'Passing Threshold' : 'Attention Required');
      document.getElementById('kpiTestRatio').innerText = `${{data.passed_cases}} / ${{data.total_cases}}`;
      document.getElementById('kpiFailedCount').innerText = `${{data.failed_cases}} failed`;

      document.getElementById('kpiLatency').innerText = `${{data.average_latency_ms.toFixed(1)}}ms`;
      const latencies = data.results.map(r => r.latency_ms).sort((a,b) => a - b);
      const p95 = latencies[Math.floor(latencies.length * 0.95)] || data.average_latency_ms;
      document.getElementById('kpiP95').innerText = `P95: ${{p95.toFixed(1)}}ms`;

      document.getElementById('kpiCost').innerText = `$${{data.total_cost_usd.toFixed(4)}}`;
      document.getElementById('kpiTokens').innerText = `Total Tokens: ${{data.total_tokens}}`;

      renderCaseTable();
    }}

    function renderCaseTable() {{
      if (!activeResult) return;
      const tbody = document.getElementById('caseTableBody');
      const search = (document.getElementById('searchFilter').value || '').toLowerCase();

      tbody.innerHTML = '';
      const filtered = activeResult.results.filter(c => {{
        if (currentFilter === 'pass' && !c.passed) return false;
        if (currentFilter === 'fail' && c.passed) return false;
        if (search && !c.case_id.toLowerCase().includes(search) && !c.case_name.toLowerCase().includes(search)) return false;
        return true;
      }});

      if (filtered.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No matching test cases found.</td></tr>';
        return;
      }}

      filtered.forEach((c, idx) => {{
        const tr = document.createElement('tr');
        tr.className = 'case-row';
        tr.onclick = () => openDrawer(c);

        const badge = c.passed
          ? '<span class="badge-status badge-pass">✓ PASS</span>'
          : '<span class="badge-status badge-fail">✗ FAIL</span>';

        const passAsserts = c.assertion_results.filter(a => a.passed).length;
        const totalAsserts = c.assertion_results.length;

        tr.innerHTML = `
          <td>${{badge}}</td>
          <td class="mono" style="color:var(--accent); font-weight:600;">${{c.case_id}}</td>
          <td>
            <div style="font-weight: 600; color:#fff;">${{c.case_name}}</div>
            <div style="font-size:0.75rem; color:var(--text-dim); margin-top:2px;">${{c.input_prompt.substring(0, 60)}}...</div>
          </td>
          <td class="mono">${{c.latency_ms.toFixed(1)}}ms</td>
          <td class="mono">${{c.token_usage.total_tokens || 0}}</td>
          <td class="mono" style="font-weight:600;">
            <span style="color: ${{passAsserts === totalAsserts ? 'var(--pass)' : 'var(--fail)'}}">${{passAsserts}}</span> / ${{totalAsserts}}
          </td>
          <td style="text-align: center;">
            <button class="btn btn-secondary" style="padding: 2px 8px; font-size:0.75rem;">View</button>
          </td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function setFilter(type) {{
      currentFilter = type;
      document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      renderCaseTable();
    }}

    function filterCases() {{
      renderCaseTable();
    }}

    function openDrawer(caseObj) {{
      document.getElementById('drawerCaseId').innerText = caseObj.case_id;
      document.getElementById('drawerCaseName').innerText = caseObj.case_name;

      const badge = document.getElementById('drawerBadge');
      badge.className = caseObj.passed ? 'badge-status badge-pass' : 'badge-status badge-fail';
      badge.innerText = caseObj.passed ? '✓ PASS' : '✗ FAIL';

      document.getElementById('drawerLatency').innerText = `${{caseObj.latency_ms.toFixed(1)}}ms latency`;
      document.getElementById('drawerTokens').innerText = `${{caseObj.token_usage.total_tokens || 0}} tokens`;

      document.getElementById('drawerPrompt').innerText = caseObj.input_prompt;
      document.getElementById('drawerOutput').innerText = caseObj.output;

      const assertContainer = document.getElementById('drawerAssertions');
      assertContainer.innerHTML = '';

      caseObj.assertion_results.forEach(a => {{
        const card = document.createElement('div');
        card.style.background = '#090e17';
        card.style.border = `1px solid ${{a.passed ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.3)'}}`;
        card.style.borderRadius = '8px';
        card.style.padding = '10px 14px';

        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="font-weight:700; font-size:0.85rem; color:${{a.passed ? 'var(--pass)' : 'var(--fail)'}};">
              ${{a.passed ? '✓' : '✗'}} [${{a.assertion_type}}] ${{a.name || ''}}
            </span>
            <span class="mono" style="font-size:0.75rem; color:var(--text-dim);">score: ${{a.score}}</span>
          </div>
          <div style="font-size:0.8rem; color:var(--text-muted);">${{a.message}}</div>
          ${{a.expected ? `<div style="font-size:0.75rem; color:var(--text-dim); margin-top:4px;">Expected: ${{JSON.stringify(a.expected)}}</div>` : ''}}
        `;
        assertContainer.appendChild(card);
      }});

      document.getElementById('drawerOverlay').style.display = 'block';
      document.getElementById('caseDrawer').style.display = 'flex';
    }}

    function closeDrawer() {{
      document.getElementById('drawerOverlay').style.display = 'none';
      document.getElementById('caseDrawer').style.display = 'none';
    }}

    /* Tab 2: Model Matrix */
    async function runMatrixBenchmark() {{
      const modelsStr = document.getElementById('matrixModelsInput').value;
      const models = modelsStr.split(',').map(m => m.trim()).filter(Boolean);
      const container = document.getElementById('matrixResultsContainer');

      container.innerHTML = '<div class="empty-state">Running benchmark across models in parallel...</div>';

      try {{
        const resp = await fetch('/api/matrix', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            suite: 'examples/05_model_matrix/suite.yaml',
            models: models
          }})
        }});

        if (!resp.ok) throw new Error(resp.statusText);
        const data = await resp.json();

        let tableHtml = `
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Model Name</th>
                <th>Pass Rate</th>
                <th>Passed / Total</th>
                <th>Avg Latency</th>
                <th>Total Cost</th>
              </tr>
            </thead>
            <tbody>
        `;

        const sorted = Object.entries(data.model_results).sort((a,b) => b[1].pass_rate - a[1].pass_rate);

        sorted.forEach(([m, res], idx) => {{
          const color = res.pass_rate >= 0.8 ? 'var(--pass)' : 'var(--fail)';
          tableHtml += `
            <tr>
              <td class="mono" style="font-weight:700;">#${{idx + 1}}</td>
              <td style="font-weight:700; color:#fff;">${{m}}</td>
              <td class="mono" style="font-weight:700; color:${{color}};">${{(res.pass_rate * 100).toFixed(1)}}%</td>
              <td class="mono">${{res.passed_cases}} / ${{res.total_cases}}</td>
              <td class="mono">${{res.average_latency_ms.toFixed(1)}}ms</td>
              <td class="mono">$${{res.total_cost_usd.toFixed(4)}}</td>
            </tr>
          `;
        }});

        tableHtml += '</tbody></table>';
        container.innerHTML = tableHtml;
      }} catch (e) {{
        container.innerHTML = `<div class="empty-state" style="color:var(--fail);">Matrix run error: ${{e}}</div>`;
      }}
    }}

    /* Tab 3: Fuzzer */
    async function runFuzzer() {{
      const container = document.getElementById('fuzzerResultsContainer');
      const modes = [];
      if (document.getElementById('fuzzTypo').checked) modes.push('typo');
      if (document.getElementById('fuzzCasing').checked) modes.push('casing');
      if (document.getElementById('fuzzNoise').checked) modes.push('noise');
      if (document.getElementById('fuzzAdv').checked) modes.push('adversarial');

      container.innerHTML = '<div class="empty-state">Generating perturbed test variations and executing stress-test...</div>';

      try {{
        const resp = await fetch('/api/fuzz', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            suite: 'examples/03_agent_safety/suite.yaml',
            modes: modes
          }})
        }});

        if (!resp.ok) throw new Error(resp.statusText);
        const data = await resp.json();

        let tableHtml = `
          <div style="padding: 1.25rem; border-bottom: 1px solid var(--card-border); display:flex; justify-content:space-between;">
            <div><strong>Fuzzed Robustness Suite:</strong> ${{data.total_cases}} cases (Stress-test result: ${{data.passed_cases}} passed)</div>
            <div style="font-weight:700; color:${{data.pass_rate >= 0.8 ? 'var(--pass)' : 'var(--fail)'}}">${{(data.pass_rate * 100).toFixed(1)}}% Pass Rate</div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Perturbed Case ID</th>
                <th>Prompt Snippet</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
        `;

        data.results.forEach(c => {{
          tableHtml += `
            <tr>
              <td><span class="badge-status ${{c.passed ? 'badge-pass' : 'badge-fail'}}">${{c.passed ? '✓ PASS' : '✗ FAIL'}}</span></td>
              <td class="mono">${{c.case_id}}</td>
              <td>${{c.input_prompt.substring(0, 90)}}...</td>
              <td class="mono">${{c.latency_ms.toFixed(1)}}ms</td>
            </tr>
          `;
        }});

        tableHtml += '</tbody></table>';
        container.innerHTML = tableHtml;
      }} catch (e) {{
        container.innerHTML = `<div class="empty-state" style="color:var(--fail);">Fuzzing error: ${{e}}</div>`;
      }}
    }}

    /* Tab 4: Studio Editor */
    async function validateYamlEditor() {{
      const text = document.getElementById('yamlEditorText').value;
      const out = document.getElementById('editorOutputBox');
      out.innerText = 'Validating schema...';

      try {{
        const resp = await fetch('/api/validate', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ content: text }})
        }});
        const data = await resp.json();
        if (data.valid) {{
          out.innerHTML = `<div style="color:var(--pass); font-weight:700;">✓ Schema Valid</div><div>Suite: ${{data.name}}</div><div>Cases Configured: ${{data.cases_count}}</div>`;
        }} else {{
          out.innerHTML = `<div style="color:var(--fail); font-weight:700;">✗ Schema Error</div><div>${{data.error}}</div>`;
        }}
      }} catch (e) {{
        out.innerText = 'Validation failed: ' + e;
      }}
    }}

    async function runCustomYamlSuite() {{
      const text = document.getElementById('yamlEditorText').value;
      const out = document.getElementById('editorOutputBox');
      out.innerText = 'Running custom suite...';

      try {{
        const resp = await fetch('/api/run', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ raw_yaml: text, simulate_success: true }})
        }});
        const data = await resp.json();
        out.innerHTML = `
          <div style="color:var(--pass); font-weight:700; margin-bottom:8px;">✓ Execution Complete</div>
          <div>Pass Rate: <strong>${{(data.pass_rate * 100).toFixed(1)}}%</strong> (${{data.passed_cases}}/${{data.total_cases}})</div>
          <div>Average Latency: ${{data.average_latency_ms.toFixed(1)}}ms</div>
          <div style="margin-top:10px;">
            <button class="btn btn-secondary" style="padding:4px 8px; font-size:0.75rem;" onclick="activeResult = ${{JSON.stringify(data)}}; switchMainTab('runner'); renderEvaluationResults(activeResult);">
              View in Main Runner Table →
            </button>
          </div>
        `;
      }} catch (e) {{
        out.innerText = 'Execution error: ' + e;
      }}
    }}

    /* Tab 5: Run History & Diff */
    async function refreshRunHistory() {{
      const container = document.getElementById('historyTableContainer');
      try {{
        const resp = await fetch('/api/history');
        const list = await resp.json();

        if (list.length === 0) {{
          container.innerHTML = '<div class="empty-state">No recorded evaluation runs yet in this session.</div>';
          return;
        }}

        let html = `
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Timestamp</th>
                <th>Suite ID</th>
                <th>Pass Rate</th>
                <th>Total Cases</th>
                <th>Avg Latency</th>
              </tr>
            </thead>
            <tbody>
        `;

        list.forEach((item, idx) => {{
          html += `
            <tr>
              <td class="mono">#${{idx + 1}}</td>
              <td class="mono" style="color:var(--text-dim);">${{item.timestamp}}</td>
              <td style="font-weight:700; color:#fff;">${{item.suite_name}}</td>
              <td class="mono" style="font-weight:700; color:${{item.pass_rate >= 0.8 ? 'var(--pass)' : 'var(--fail)'}}">${{(item.pass_rate * 100).toFixed(1)}}%</td>
              <td class="mono">${{item.passed_cases}} / ${{item.total_cases}}</td>
              <td class="mono">${{item.average_latency_ms.toFixed(1)}}ms</td>
            </tr>
          `;
        }});

        html += '</tbody></table>';
        container.innerHTML = html;
      }} catch (e) {{
        container.innerHTML = `<div class="empty-state">Error fetching history: ${{e}}</div>`;
      }}
    }}

    /* Exports */
    function exportJsonResults() {{
      if (!activeResult) return alert('No evaluation run available to export.');
      const blob = new Blob([JSON.stringify(activeResult, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `veridex_result_${{activeResult.suite_id || 'eval'}}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }}

    function exportMarkdownPR() {{
      if (!activeResult) return alert('No evaluation run available.');
      let md = `### 🛡️ Veridex Evaluation Report (${{activeResult.suite_name}})\\n\\n`;
      md += `| Status | Passed / Total | Pass Rate | Avg Latency | Total Cost |\\n`;
      md += `| :--- | :---: | :---: | :---: | :---: |\\n`;
      md += `| ${{activeResult.pass_rate >= 0.8 ? '✅ PASS' : '❌ FAIL'}} | ${{activeResult.passed_cases}}/${{activeResult.total_cases}} | **${{(activeResult.pass_rate * 100).toFixed(1)}}%** | ${{activeResult.average_latency_ms.toFixed(1)}}ms | \\$${{activeResult.total_cost_usd.toFixed(4)}} |\\n\\n`;
      navigator.clipboard.writeText(md);
      alert('GitHub PR Markdown summary copied to clipboard!');
    }}
  </script>
</body>
</html>"""


class VeridexStudioHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path in ("/", "/index.html"):
            html = _get_enterprise_studio_html()
            self._send_response_data(200, "text/html; charset=utf-8", html.encode("utf-8"))
        elif path == "/api/status":
            resp = json.dumps({"status": "ok", "version": __version__, "platform": "Veridex Enterprise Studio"})
            self._send_response_data(200, "application/json", resp.encode("utf-8"))
        elif path == "/api/history":
            resp = json.dumps(RUN_HISTORY)
            self._send_response_data(200, "application/json", resp.encode("utf-8"))
        elif path == "/api/suites":
            suites = self._discover_suites()
            self._send_response_data(200, "application/json", json.dumps(suites).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length)

        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as e:
            self._send_error(400, f"Malformed JSON request: {e}")
            return

        if path == "/api/run":
            self._handle_run(payload)
        elif path == "/api/matrix":
            self._handle_matrix(payload)
        elif path == "/api/fuzz":
            self._handle_fuzz(payload)
        elif path == "/api/validate":
            self._handle_validate(payload)
        elif path == "/api/diff":
            self._handle_diff(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_run(self, payload: Dict[str, Any]) -> None:
        try:
            raw_yaml = payload.get("raw_yaml")
            suite_source = payload.get("suite", "examples/01_structured_extraction/suite.yaml")
            sim_success = payload.get("simulate_success", False)

            if raw_yaml:
                suite = SuiteLoader.load_from_string(raw_yaml)
            else:
                suite = SuiteLoader.load_from_source(suite_source)

            runner = TestRunner()
            if sim_success and suite.provider == "mock":
                runner.provider = MockProvider(model=suite.model or "mock-model", simulate_success=True)

            result = asyncio.run(runner.run_suite(suite))
            result_dict = result.model_dump(mode="json")

            # Save in run history (keep last 50 runs)
            RUN_HISTORY.append({
                "suite_id": result.suite_id,
                "suite_name": result.suite_name,
                "timestamp": result.timestamp,
                "pass_rate": result.pass_rate,
                "passed_cases": result.passed_cases,
                "failed_cases": result.failed_cases,
                "total_cases": result.total_cases,
                "average_latency_ms": result.average_latency_ms,
                "total_cost_usd": result.total_cost_usd,
            })
            if len(RUN_HISTORY) > 50:
                RUN_HISTORY.pop(0)

            self._send_response_data(200, "application/json", json.dumps(result_dict).encode("utf-8"))
        except Exception as e:
            self._send_error(400, str(e))

    def _handle_matrix(self, payload: Dict[str, Any]) -> None:
        try:
            suite_source = payload.get("suite", "examples/05_model_matrix/suite.yaml")
            models = payload.get("models", ["mock-fast", "mock-smart"])
            suite = SuiteLoader.load_from_source(suite_source)

            matrix = asyncio.run(MatrixRunner.run_matrix(suite, models=models))
            self._send_response_data(200, "application/json", matrix.model_dump_json().encode("utf-8"))
        except Exception as e:
            self._send_error(400, str(e))

    def _handle_fuzz(self, payload: Dict[str, Any]) -> None:
        try:
            suite_source = payload.get("suite", "examples/03_agent_safety/suite.yaml")
            modes = payload.get("modes", ["typo", "casing", "noise", "adversarial"])
            suite = SuiteLoader.load_from_source(suite_source)

            fuzzed_suite = SuiteFuzzer.fuzz_suite(suite, modes=modes)
            runner = TestRunner()
            result = asyncio.run(runner.run_suite(fuzzed_suite))
            self._send_response_data(200, "application/json", result.model_dump_json().encode("utf-8"))
        except Exception as e:
            self._send_error(400, str(e))

    def _handle_validate(self, payload: Dict[str, Any]) -> None:
        try:
            content = payload.get("content", "")
            suite = SuiteLoader.load_from_string(content)
            resp = {
                "valid": True,
                "id": suite.id,
                "name": suite.name,
                "cases_count": len(suite.cases),
            }
            self._send_response_data(200, "application/json", json.dumps(resp).encode("utf-8"))
        except Exception as e:
            resp = {"valid": False, "error": str(e)}
            self._send_response_data(200, "application/json", json.dumps(resp).encode("utf-8"))

    def _handle_diff(self, payload: Dict[str, Any]) -> None:
        try:
            base_data = payload.get("baseline")
            curr_data = payload.get("candidate")
            from veridex.core.models import SuiteResult
            base = SuiteResult.model_validate(base_data)
            curr = SuiteResult.model_validate(curr_data)
            diff = SuiteComparator.compare(base, curr)
            self._send_response_data(200, "application/json", diff.model_dump_json().encode("utf-8"))
        except Exception as e:
            self._send_error(400, str(e))

    def _discover_suites(self) -> List[Dict[str, Any]]:
        suites = []
        for path in Path("examples").glob("**/suite.yaml"):
            try:
                s = SuiteLoader.load_from_file(path)
                suites.append({
                    "path": str(path).replace("\\", "/"),
                    "id": s.id,
                    "name": s.name,
                    "cases": len(s.cases),
                })
            except Exception:
                continue
        return suites

    def _send_response_data(self, code: int, content_type: str, data: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, code: int, message: str) -> None:
        err_json = json.dumps({"error": message}).encode("utf-8")
        self._send_response_data(code, "application/json", err_json)


def run_studio_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = HTTPServer((host, port), VeridexStudioHandler)
    print(f"\n==================================================================")
    print(f"⚡ VERIDEX ENTERPRISE STUDIO LIVE at: http://{host}:{port}/")
    print(f"==================================================================")
    print(f"• Evaluation Runner & Filter Engine")
    print(f"• Model Matrix Leaderboard")
    print(f"• Adversarial Fuzzer & Stress Lab")
    print(f"• In-Browser YAML Suite Studio")
    print(f"• Regression Diff & Historical Baselines")
    print(f"Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Veridex Studio...")
        server.server_close()