# Veridex

> High-Precision Evaluation, Regression Testing & Reliability Harness for LLMs and AI Agents.

Veridex is an asynchronous testing and reliability framework built in Python for applied AI engineering teams developing LLM-powered applications, autonomous agents, and RAG pipelines. It helps detect behavioral regressions, benchmark model transitions, and enforce structured output guarantees before production deployment.

🌐 **Website & Live Documentation:** [https://pooya-labs.github.io/veridex/](https://pooya-labs.github.io/veridex/)

---

## Key Capabilities

- **Deterministic Assertions**: JSON Schema validation, regex patterns, substring assertions, latency limits, and token budgets.
- **RAG Faithfulness & Groundedness**: Verify responses are strictly grounded in retrieved knowledge context, penalize unsupported numerical claims, and evaluate prompt intent relevance.
- **Code & SQL Guards**: AST Python syntax parsing, SQL query structure validation, dangerous query prevention (unconstrained DELETE/DROP), and nested JSON Path evaluation.
- **Similarity & Overlap Metrics**: Normalized Levenshtein distance, Jaccard set index, and token-level Precision/Recall/F1 scores.
- **Safety & Guardrails**: Built-in detection for sensitive data leaks (emails, credentials, API keys, Luhn-verified card numbers) and prompt injection/jailbreak attempts.
- **Model Benchmark Matrix**: Cross-benchmark multiple LLMs (e.g., GPT-4o, Gemini 1.5, Claude 3.5, Llama 3) in parallel and output an automated Leaderboard with pass rates, latency, and token cost (`veridex matrix`).
- **Adversarial Fuzzing & Stress Testing**: Automatically perturb test suites with typo injection, casing flips, conversational noise, and jailbreak probes to evaluate prompt robustness (`veridex fuzz`).
- **Veridex Studio (Web UI)**: Launch a zero-dependency local web studio to run suites and inspect failures interactively in your browser (`veridex serve`).
- **Remote Suite Loading**: Fetch and run evaluation suites directly from remote URLs or GitHub raw links (`veridex run https://...`).
- **Live Endpoint / Webhook Evaluation**: Test live deployed APIs, FastAPI backends, and microservices directly using the built-in HTTP provider (`-p http -u "https://..."`).
- **Regression Analysis**: Direct delta comparison between baseline runs and candidate runs (`veridex compare baseline.json current.json`).
- **Pytest SDK Integration**: Seamlessly integrate LLM assertions into standard Python CI test suites with `assert_eval(...)`.
- **Rich Reports & Dashboards**: Terminal Rich tables, failure diagnostics, JSON exports, GitHub PR-ready Markdown reports, and interactive standalone HTML dashboards (`-H report.html`).

---

## Project Structure

```text
veridex/
├── pyproject.toml              # Packaging and dependency declarations
├── action.yml                  # GitHub Actions composite action
├── veridex/
│   ├── cli.py                  # Command-line interface (run, matrix, fuzz, compare, serve, init)
│   ├── server.py               # Built-in lightweight Veridex Studio Web Server
│   ├── sdk.py                  # Programmatic Pytest integration (assert_eval)
│   ├── core/
│   │   ├── models.py           # Pydantic v2 schemas (Suite, Case, Results, Assertions)
│   │   ├── runner.py           # Concurrency-controlled async runner (asyncio.Semaphore)
│   │   ├── reporter.py         # Terminal (Rich), JSON, and Markdown reporters
│   │   ├── html_reporter.py    # Interactive standalone web dashboard reporter
│   │   ├── diff.py             # Regression detection and comparison engine
│   │   ├── matrix.py           # Multi-model benchmarking runner & leaderboard
│   │   └── fuzzer.py           # Adversarial perturbation & stress testing engine
│   ├── evaluators/             # Deterministic, similarity, safety, code/SQL, RAG, and judge
│   ├── providers/              # Mock, Gemini, OpenAI, and HTTP REST endpoint adapters
│   └── loaders/                # Local & remote (HTTP) test suite loader
├── docs/                       # GitHub Pages live interactive playground
├── examples/                   # Production-ready test suites (01 through 05)
└── tests/                      # Comprehensive unit test suite (32 tests)
```

---

## Quickstart

### 1. Installation

```bash
pip install -e .
```

### 2. Launch Veridex Studio (Web UI)

Run the zero-dependency local interactive studio:

```bash
veridex serve --port 8080
```
Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) in your browser to run evaluations and inspect test diagnostics with one click.

### 3. Run an Evaluation & Export Interactive HTML Report

```bash
veridex run examples/01_structured_extraction/suite.yaml \
  -o results.json \
  -m report.md \
  -H dashboard.html
```

### 4. Run Directly from a Remote URL / GitHub Link

```bash
veridex run https://raw.githubusercontent.com/pooya-labs/veridex/main/examples/02_rag_hallucination/suite.yaml --simulate-success
```

### 5. Multi-Model Benchmark Matrix & Leaderboard

Compare accuracy, latency, and cost across multiple models:

```bash
veridex matrix examples/05_model_matrix/suite.yaml -m gpt-4o,claude-3-5-sonnet,gemini-1.5-pro
```

### 6. Fuzz & Stress Test Prompt Robustness

Generate adversarial perturbations (typos, casing, noise, jailbreak probes):

```bash
veridex fuzz examples/03_agent_safety/suite.yaml --run
```

### 7. Evaluate Live Deployed Microservice or Webhook

```bash
veridex run suite.yaml -p http -u "https://my-rag-backend.com/api/chat"
```

### 8. Detect Regressions in CI/CD

```bash
veridex compare baseline.json candidate.json
```

---

## Pytest SDK Usage

You can also use Veridex directly inside standard Pytest test functions:

```python
from veridex.sdk import assert_eval

def test_ai_customer_support_intent():
    model_output = '{"intent": "refund_request", "confidence": 0.96}'

    assert_eval(
        output=model_output,
        assertions=[
            {"type": "valid_json"},
            {"type": "json_path", "value": "intent", "expected": "refund_request"},
            {"type": "no_pii"},
        ]
    )
```

---

## Author & Attribution

Developed by **Pooya Goodarzi** ([pooya-labs](https://github.com/pooya-labs)).  
Licensed under the [MIT License](LICENSE).
