# Veridex

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/tests-50%20passed-brightgreen.svg)](https://github.com/pooya-labs/veridex/actions)
[![Docs & Live Demo](https://img.shields.io/badge/docs-interactive%20demo-cyan.svg)](https://pooya-labs.github.io/veridex/)

> High-Precision Evaluation, Regression Testing & Reliability Harness for LLMs and Applied AI Systems.

Veridex is an asynchronous testing, reliability, and monitoring framework built in Python for applied AI engineering teams developing LLM-powered applications, autonomous agents, and RAG pipelines. It helps generate synthetic test datasets, detect behavioral regressions, benchmark model transitions, and enforce real-time output guardrails before and after production deployment.

🌐 **Website & Live Playground:** [https://pooya-labs.github.io/veridex/](https://pooya-labs.github.io/veridex/)

---

## Key Capabilities

- **Synthetic Test Dataset Generator**: Automatically synthesize full golden test suites from domain topics or archetypes (`json`, `rag`, `safety`, `sql`, `general`) with `veridex generate`.
- **Runtime Guardrails & Observability**: Real-time drop-in protection with `guard(...)` and `@monitor` decorator to intercept PII leaks, prompt injections, and schema violations in production APIs.
- **Deterministic Assertions**: JSON Schema validation, regex patterns, substring assertions, latency limits, and token budgets.
- **RAG Faithfulness & Groundedness**: Verify responses are strictly grounded in retrieved knowledge context, penalize unsupported numerical claims, and evaluate prompt intent relevance.
- **Code & SQL Guards**: AST Python syntax parsing, SQL query structure validation, dangerous query prevention (unconstrained DELETE/DROP), and nested JSON Path evaluation.
- **Similarity & Overlap Metrics**: Normalized Levenshtein distance, Jaccard set index, and token-level Precision/Recall/F1 scores.
- **Safety & Guardrails**: Built-in detection for sensitive data leaks (emails, credentials, API keys, Luhn-verified card numbers) and prompt injection/jailbreak attempts.
- **Model Benchmark Matrix**: Cross-benchmark multiple LLMs (e.g., GPT-4o, Gemini 1.5, Claude 3.5, Llama 3) in parallel and output an automated Leaderboard with pass rates, latency, and token cost (`veridex matrix`).
- **Adversarial Fuzzing & Stress Testing**: Automatically perturb test suites with typo injection, casing flips, conversational noise, and jailbreak probes to evaluate prompt robustness (`veridex fuzz`).
- **Veridex Enterprise Studio (Web UI)**: Launch a zero-dependency local web studio with 5 modular tabs (Runner, Matrix, Fuzzer, YAML Studio with live validation & synthesis, Regression Diff) via `veridex serve`.
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
│   ├── cli.py                  # CLI (run, generate, matrix, fuzz, compare, serve, init)
│   ├── server.py               # Veridex Enterprise Studio Web Server (5 modular tabs)
│   ├── sdk.py                  # Programmatic Pytest integration (assert_eval)
│   ├── integrations/           # Guardrails (@monitor, guard), LangChain & OpenTelemetry tracing
│   ├── core/
│   │   ├── models.py           # Pydantic v2 schemas (Suite, Case, Results, Assertions)
│   │   ├── runner.py           # Concurrency-controlled async runner (asyncio.Semaphore)
│   │   ├── generator.py        # Automated synthetic test suite & golden dataset generator
│   │   ├── reporter.py         # Terminal (Rich), JSON, and Markdown reporters
│   │   ├── html_reporter.py    # Interactive standalone web dashboard reporter
│   │   ├── diff.py             # Regression detection and comparison engine
│   │   ├── matrix.py           # Multi-model benchmarking runner & leaderboard
│   │   └── fuzzer.py           # Adversarial perturbation & stress testing engine
│   ├── evaluators/             # Deterministic, similarity, safety, code/SQL, RAG, and judge
│   ├── providers/              # Mock, Gemini, OpenAI, and HTTP REST endpoint adapters
│   └── loaders/                # Local, string, and remote (HTTP) test suite loaders
├── docs/                       # GitHub Pages live interactive playground
├── examples/                   # Production-ready test suites (01 through 05)
└── tests/                      # Comprehensive unit test suite (48 tests, 100% pass)
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
Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) in your browser to run evaluations, test matrix models, fuzz prompts, and synthesize suites with 1 click.

### 3. Synthesize a Test Suite from Scratch

Automatically generate a 5-case golden evaluation suite for your domain:

```bash
veridex generate -t "ecommerce_refunds" --template json -n 5 -o my_suite.yaml --run --simulate-success
```

### 4. Run an Evaluation & Export Interactive HTML Report

```bash
veridex run examples/01_structured_extraction/suite.yaml \
  -o results.json \
  -m report.md \
  -H dashboard.html
```

### 5. Run Directly from a Remote URL / GitHub Link

```bash
veridex run https://raw.githubusercontent.com/pooya-labs/veridex/main/examples/02_rag_hallucination/suite.yaml --simulate-success
```

### 6. Multi-Model Benchmark Matrix & Leaderboard

Compare accuracy, latency, and cost across multiple models:

```bash
veridex matrix examples/05_model_matrix/suite.yaml -m gpt-4o claude-3-5-sonnet gemini-1.5-pro
```

### 7. Fuzz & Stress Test Prompt Robustness

Generate adversarial perturbations (typos, casing, noise, jailbreak probes):

```bash
veridex fuzz examples/03_agent_safety/suite.yaml --run
```

### 8. Detect Regressions & Gate CI/CD Pull Requests

Compare baseline vs candidate runs, generate GitHub Flavored Markdown summaries for PR comments, and gate merges on regressions (exit code 3):

```bash
veridex compare baseline.json candidate.json \
  --github-summary \
  --output-md pr_diff.md \
  --fail-on-regression
```

---

## Integrations: LangChain & OpenTelemetry Tracing

### LangChain Integration

Plug `VeridexCallbackHandler` directly into any LangChain model or agent chain to validate outputs, track latencies, and prevent violations:

```python
from veridex import VeridexCallbackHandler, Assertion

handler = VeridexCallbackHandler(
    assertions=[
        Assertion(type="valid_json"),
        Assertion(type="no_pii"),
    ],
    raise_on_violation=True,
)

# Pass directly to LangChain model invocations:
response = llm.invoke("Generate invoice payload", config={"callbacks": [handler]})
print(handler.get_summary())
```

### OpenTelemetry GenAI Telemetry

Capture structured OpenTelemetry spans with token counts, latency, and assertion status:

```python
from veridex import VeridexTracer

tracer = VeridexTracer(service_name="payment-agent")

with tracer.trace("fraud_evaluation", model="gpt-4o", provider="openai") as span:
    span.set_attribute("gen_ai.request.temperature", 0.2)
    # execute LLM logic ...

tracer.export_jsonl("logs/genai_telemetry.jsonl")
```

---

## Production Runtime Guardrails & Monitoring

Protect your live applications and agents against PII leaks, injections, and hallucinations in real time:

```python
from veridex import guard, monitor, GuardrailViolation

# 1. Inline Guardrail Enforcement
clean_output = guard(
    output=llm_response,
    assertions=[
        {"type": "no_pii"},
        {"type": "no_jailbreak"},
        {"type": "valid_json"},
    ],
    fallback='{"status": "blocked_by_safety_policy"}'
)

# 2. Decorator for LLM Generation Endpoints
@monitor(assertions=["no_pii", "no_jailbreak"])
def call_agent(prompt: str) -> str:
    return openai_client.chat(prompt)
```

---

## Pytest SDK Usage

Integrate LLM assertions directly inside your Pytest suites:

```python
from veridex import assert_eval

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

## Custom Evaluator Plugins

Register domain-specific evaluators with the `@register_evaluator` decorator and use them anywhere in YAML test suites, runtime guardrails, or programmatic checks:

```python
from veridex import register_evaluator, guard

@register_evaluator("polite_tone")
def check_polite(output: str, **kwargs) -> bool:
    return any(p in output.lower() for p in ["please", "thank you", "kind regards"])

# Use in runtime guardrails or YAML test suites
safe_response = guard(
    output="Thank you for reaching out! Your order has shipped.",
    assertions=[{"type": "polite_tone"}],
    fallback="Apologies, please contact customer care directly."
)
```

---

## Author & Attribution

Developed by **Pooya Goodarzi** ([pooya-labs](https://github.com/pooya-labs)).  
Released under the [MIT License](LICENSE).
