# Veridex

> High-Precision Evaluation, Regression Testing & Reliability Harness for LLMs and AI Agents.

Veridex is an asynchronous testing framework built in Python for teams developing LLM-powered applications, autonomous agents, and RAG pipelines. It helps detect behavioral regressions, benchmark model transitions, and enforce structured output guarantees before production deployment.

🌐 **Website & Live Demo:** [https://pooya-labs.github.io/veridex/](https://pooya-labs.github.io/veridex/)

---

## Key Capabilities

- **Deterministic Assertions**: JSON Schema validation, regex patterns, substring assertions, latency limits, and token budgets.
- **Code & SQL Guards**: AST Python syntax validation, SQL query structure validation, dangerous SQL prevention (unconstrained DELETE/DROP), and nested JSON Path evaluation.
- **Similarity & Overlap Metrics**: Levenshtein distance, Jaccard set index, and token-level Precision/Recall/F1 scores.
- **Safety & Guardrails**: Built-in detection for sensitive data leaks (emails, credentials, API keys, Luhn-verified card numbers) and prompt injection attempts.
- **Remote Suite Loading**: Fetch and run evaluation suites directly from remote URLs or GitHub raw links (`veridex run https://...`).
- **Live Endpoint / Webhook Evaluation**: Test live deployed APIs, FastAPI backends, and microservices directly using the built-in HTTP provider.
- **Regression Analysis**: Direct delta comparison between baseline runs and candidate runs (`veridex compare baseline.json current.json`).
- **Flexible Providers**: Native support for Mock testing (zero API cost), Google Gemini, OpenAI-compatible endpoints (Ollama, vLLM, OpenRouter), and custom HTTP/REST endpoints.
- **Rich Reports & Web Dashboards**: Color-coded terminal summaries, failure diagnostics, JSON exports, GitHub PR-ready Markdown reports, and interactive standalone HTML dashboards (`-H report.html`).

---

## Project Structure

```text
veridex/
├── pyproject.toml              # Packaging and dependency declarations
├── veridex/
│   ├── cli.py                  # Command-line interface
│   ├── core/
│   │   ├── models.py           # Pydantic schemas (Suite, Case, Results)
│   │   ├── runner.py           # Concurrency-controlled async runner
│   │   ├── reporter.py         # Terminal, JSON, and Markdown reporters
│   │   ├── html_reporter.py    # Interactive web dashboard reporter
│   │   └── diff.py             # Regression detection and comparison
│   ├── evaluators/             # Deterministic, similarity, safety, code/SQL, and judge evaluators
│   ├── providers/              # Mock, Gemini, OpenAI, and HTTP REST endpoint adapters
│   └── loaders/                # Local & remote (HTTP) test suite loader
├── docs/                       # GitHub Pages interactive documentation
├── examples/                   # Structured extraction, RAG, and safety suites
└── tests/                      # Unit test suite (17 tests)
```

---

## Quickstart

### 1. Installation

```bash
pip install -e .
```

### 2. Validate a Test Suite (Local or Remote)

```bash
# Validate local file
veridex validate examples/01_structured_extraction/suite.yaml

# Validate directly from remote URL
veridex validate https://raw.githubusercontent.com/pooya-labs/veridex/main/examples/02_rag_hallucination/suite.yaml
```

### 3. Run an Evaluation & Generate Interactive HTML Dashboard

```bash
veridex run examples/01_structured_extraction/suite.yaml -o results.json -m report.md -H dashboard.html
```

### 4. Evaluate a Live Deployed Backend / RAG Service

```bash
veridex run suite.yaml -p http -u "https://my-rag-backend.com/api/chat"
```

### 5. Detect Regressions Across Runs

```bash
veridex compare baseline.json candidate.json
```

---

## Author & Attribution

Developed by **Pooya Goodarzi** ([pooya-labs](https://github.com/pooya-labs)).  
Licensed under the [MIT License](LICENSE).
