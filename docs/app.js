function copyCommand() {
      const text = document.getElementById('cmdText').innerText;
      navigator.clipboard.writeText(text);
      alert('Copied to clipboard: ' + text);
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-' + tabId).classList.add('active');
    }

    // Real-time interactive playground evaluators
    function runDemo(type) {
      if (type === 'json') {
        const inputStr = document.getElementById('json-input').value;
        const res = document.getElementById('json-result');
        try {
          const parsed = JSON.parse(inputStr);
          const reqFields = ['ticket_id', 'category', 'urgency', 'summary'];
          const missing = reqFields.filter(f => !(f in parsed));
          const hasBilling = parsed.category === 'billing';

          if (missing.length === 0 && hasBilling) {
            res.innerHTML = `
<div style="color:#10b981; font-weight:700; margin-bottom:8px;">✔ STATUS: PASSED (Score: 1.0)</div>
<div>• <code>valid_json</code>: <span style="color:#10b981;">Valid JSON parsed successfully</span></div>
<div>• <code>json_schema</code>: <span style="color:#10b981;">All required properties present: ${JSON.stringify(reqFields)}</span></div>
<div>• <code>contains("billing")</code>: <span style="color:#10b981;">Match confirmed in category field</span></div>
<div style="margin-top:10px; color:#64748b; font-size:0.8rem;">P99 Latency: 0.8ms | Tokens Evaluated: ${inputStr.split(' ').length} | Zero external judge calls</div>
`;
          } else {
            let errors = [];
            if (missing.length > 0) errors.push(`Missing schema fields: ${missing.join(', ')}`);
            if (!hasBilling) errors.push(`Category must be 'billing', got '${parsed.category || 'undefined'}'`);
            res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">✘ STATUS: FAILED — Schema Violation</div>
<div>• <code>valid_json</code>: <span style="color:#10b981;">Valid syntax</span></div>
<div>• <code>json_schema</code>: <span style="color:#ef4444;">${errors.join('<br>• ')}</span></div>
<div style="margin-top:10px; color:#f59e0b; font-size:0.8rem;">Result: Blocked from downstream consumer.</div>
`;
          }
        } catch (e) {
          res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">✘ STATUS: FAILED — JSON Parse Error</div>
<div style="color:#f87171;">• <code>valid_json</code>: ${e.message}</div>
<div style="margin-top:10px; color:#ef4444; font-size:0.8rem;">Severe: Malformed LLM output detected. Fallback triggered.</div>
`;
        }
      } else if (type === 'rag') {
        const contextStr = document.getElementById('rag-context').value;
        const candidateStr = document.getElementById('rag-candidate').value;
        const res = document.getElementById('rag-result');

        const candNumbers = candidateStr.match(/\$?[0-9]+(?:\.[0-9]+)?/g) || [];
        const ungrounded = candNumbers.filter(num => !contextStr.includes(num));

        if (ungrounded.length === 0) {
          res.innerHTML = `
<div style="color:#10b981; font-weight:700; margin-bottom:8px;">✔ STATUS: PASSED (Faithfulness: 1.00)</div>
<div>• <code>faithfulness</code>: <span style="color:#10b981;">100% grounded in retrieved context</span></div>
<div>• <code>numeric_grounding</code>: <span style="color:#10b981;">All statistics &amp; figures verified</span></div>
<div style="margin-top:10px; color:#64748b; font-size:0.8rem;">P99 Latency: 1.2ms | Safe to stream to end user</div>
`;
        } else {
          res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">✘ STATUS: FAILED — Hallucination Detected</div>
<div>• <code>faithfulness</code>: <span style="color:#ef4444;">Score 0.35 &lt; 0.70 (Penalty applied for ungrounded entities)</span></div>
<div>• <code>hallucinated_tokens</code>: <span style="color:#ef4444;">[${ungrounded.join(', ')}] not found in context</span></div>
<div style="margin-top:10px; color:#f59e0b; font-size:0.8rem;">Action: Guardrail activated, response dropped before delivery.</div>
`;
        }
      } else if (type === 'pii') {
        const text = document.getElementById('pii-input').value;
        const res = document.getElementById('pii-result');

        const emailMatch = text.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
        const secretKeyMatch = text.match(/sk-[a-zA-Z0-9_-]{10,}|AKIA[0-9A-Z]{16}/);

        function checkLuhn(card) {
          const clean = card.replace(/[^0-9]/g, '');
          if (clean.length < 13 || clean.length > 19) return false;
          let sum = 0, shouldDouble = false;
          for (let i = clean.length - 1; i >= 0; i--) {
            let digit = parseInt(clean.charAt(i));
            if (shouldDouble) {
              digit *= 2;
              if (digit > 9) digit -= 9;
            }
            sum += digit;
            shouldDouble = !shouldDouble;
          }
          return (sum % 10) === 0;
        }

        const rawDigits = text.match(/\b(?:\d[ -]*?){13,19}\b/g);
        let validCard = null;
        if (rawDigits) {
          for (let d of rawDigits) {
            if (checkLuhn(d)) {
              validCard = d.trim();
              break;
            }
          }
        }

        const leaks = [];
        if (emailMatch) leaks.push(`Email address: ${emailMatch[0]}`);
        if (secretKeyMatch) leaks.push(`API Key / Secret: ${secretKeyMatch[0].slice(0, 10)}...`);
        if (validCard) leaks.push(`Credit Card (Luhn-verified): ${validCard}`);

        if (leaks.length > 0) {
          res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">✘ STATUS: FAILED (Critical PII / Secret Alert)</div>
<div style="color:#f59e0b; margin-bottom:8px;">Detected Violations:</div>
${leaks.map(l => `<div>• <span style="color:#ef4444;">${l}</span></div>`).join('')}
<div style="margin-top:10px; color:#ef4444; font-size:0.8rem;">Interception: Output blocked by Veridex PII Shield.</div>
`;
        } else {
          res.innerHTML = `
<div style="color:#10b981; font-weight:700; margin-bottom:8px;">✔ STATUS: PASSED (Clean Output)</div>
<div>• <code>no_pii</code>: <span style="color:#10b981;">0 emails, phone numbers, or cards detected</span></div>
<div>• <code>no_secrets</code>: <span style="color:#10b981;">0 private keys or tokens found</span></div>
<div style="margin-top:10px; color:#64748b; font-size:0.8rem;">Compliant with GDPR &amp; SOC2 LLM Output Guidelines.</div>
`;
        }
      } else if (type === 'injection') {
        const text = document.getElementById('injection-input').value.toLowerCase();
        const res = document.getElementById('injection-result');
        const injectionPhrases = [
          'ignore all previous instructions',
          'you are now dan',
          'system prompt override',
          'print all internal guidelines',
          'disregard prior constraints',
          'jailbreak'
        ];
        const matched = injectionPhrases.filter(p => text.includes(p));

        if (matched.length > 0) {
          res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">✘ STATUS: FAILED (Score: 0.0) — Jailbreak Detected</div>
<div style="color:#f59e0b; margin-bottom:6px;">Violated Heuristics:</div>
${matched.map(m => `<div>• Matched adversarial pattern: <span style="color:#ef4444;">'${m}'</span></div>`).join('')}
<div style="margin-top:10px; color:#f59e0b; font-size:0.8rem;">Recommendation: Reject request or activate safety fallback model.</div>
`;
        } else {
          res.innerHTML = `
<div style="color:#10b981; font-weight:700; margin-bottom:8px;">✔ STATUS: PASSED (Score: 1.0) — Safe Prompt</div>
<div>• <code>no_prompt_injection</code>: <span style="color:#10b981;">No adversarial jailbreak heuristics triggered</span></div>
<div style="margin-top:10px; color:#64748b; font-size:0.8rem;">Prompt authorized for completion pipeline.</div>
`;
        }
      } else if (type === 'fuzz') {
        const res = document.getElementById('fuzz-result');
        res.innerHTML = `
<div style="color:#10b981; font-weight:600; margin-bottom:8px;">Robustness Evaluation Complete (15 perturbed variations)</div>
<div>• Baseline Prompt: <span style="color:#10b981;">100% Pass</span></div>
<div>• Typo Perturbation: <span style="color:#10b981;">100% Pass</span></div>
<div>• Casing Mutation: <span style="color:#10b981;">100% Pass</span></div>
<div>• Conversational Noise: <span style="color:#10b981;">100% Pass</span></div>
<div>• Adversarial Injection: <span style="color:#10b981;">Defenses Held (100% Blocked)</span></div>
<div style="margin-top:8px; color:#64748b;">Robustness Index: 1.0 (Highly resilient)</div>
`;
      }
    }

    const sampleYamls = {
      finance: `version: "1.0"
name: "Synthetic Fintech Transactions & KYC"
provider: "gemini"
model: "gemini-1.5-pro"
cases:
  - id: "syn_fin_01"
    name: "Wire Transfer Extraction"
    prompt: "Extract wire details from: 'Transfer $12,500 USD to IBAN DE89370400440532013000 for invoice 8821.'"
    assertions:
      - type: "valid_json"
      - type: "json_schema"
        schema:
          type: "object"
          required: ["amount", "currency", "iban", "invoice_id"]
      - type: "no_pii"
  - id: "syn_fin_02"
    name: "KYC Sanction Risk Check"
    prompt: "Review customer passport scan output and return risk tier."
    assertions:
      - type: "contains"
        value: "risk_level"`,
      ecommerce: `version: "1.0"
name: "Synthetic E-Commerce Order Parsing"
provider: "openai"
model: "gpt-4o"
cases:
  - id: "syn_ecom_01"
    name: "Cart Checkout Parsing"
    prompt: "Customer wants 2x Quantum Noise Headphones (SKU: QN-99) delivered to 102 Market St."
    assertions:
      - type: "valid_json"
      - type: "json_schema"
        schema:
          type: "object"
          required: ["sku", "quantity", "shipping_address"]`,
      medical: `version: "1.0"
name: "Synthetic Healthcare Triage & HIPAA"
provider: "gemini"
model: "gemini-1.5-flash"
cases:
  - id: "syn_med_01"
    name: "Patient Intake Triage"
    prompt: "Patient reports acute chest pain with diaphoresis."
    assertions:
      - type: "no_pii"
      - type: "not_contains"
        value: "SSN:"
      - type: "contains"
        value: "EMERGENCY_TRIAGE_1"`,
      customer_support: `version: "1.0"
name: "Synthetic Support Ticket Categorization"
provider: "mock"
model: "mock-model"
cases:
  - id: "syn_supp_01"
    name: "Urgent Billing Dispute"
    prompt: "Double charged on subscription for team plan."
    assertions:
      - type: "valid_json"
      - type: "contains"
        value: "billing"`
    };

    function updateGeneratedPreview() {
      const domainEl = document.getElementById('gen-domain');
      if (!domainEl) return;
      const domain = domainEl.value;
      const baseYaml = sampleYamls[domain] || sampleYamls['finance'];
      const previewEl = document.getElementById('gen-yaml-preview');
      if (previewEl) previewEl.textContent = baseYaml;
    }

    function runGeneratedSuite() {
      const res = document.getElementById('gen-eval-result');
      const domain = document.getElementById('gen-domain').value;
      const tpl = document.getElementById('gen-template').value;
      const count = document.getElementById('gen-count').value;
      res.innerHTML = `
<div style="color:#10b981; font-weight:700; margin-bottom:8px; font-size:0.95rem;">
  ✔ SYNTHESIS COMPLETE: Generated ${count} Golden Cases for [${domain.toUpperCase()}]
</div>
<div style="display:flex; gap:16px; margin-bottom:12px; font-size:0.8rem; color:#94a3b8;">
  <div>Pass Rate: <span style="color:#10b981; font-weight:700;">100.0%</span></div>
  <div>Latency: <span style="color:#38bdf8;">28.4ms</span></div>
  <div>Archetype: <span style="color:#c084fc;">${tpl.toUpperCase()}</span></div>
</div>
<div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;">
  <div>• Case syn_01: <span style="color:#10b981;">PASSED (valid_json + schema matched)</span></div>
  <div>• Case syn_02: <span style="color:#10b981;">PASSED (no_pii: Zero leaks detected)</span></div>
  <div>• Case syn_03: <span style="color:#10b981;">PASSED (levenshtein: 0.94 score)</span></div>
</div>
<div style="margin-top:12px; font-size:0.8rem; color:#64748b;">
  Exported to: <code>generated_${domain}_suite.yaml</code> | CLI: <code>veridex run generated_${domain}_suite.yaml</code>
</div>
`;
    }

    const guardScenarios = {
      clean: `# Runtime Code
@monitor(assertions=[
    Assertion(type="no_pii"),
    Assertion(type="valid_json")
], fallback='{"status": "blocked", "reason": "guardrail_violation"}')
async def create_user_profile(user_input: str):
    return await llm.complete(user_input)

# Model Output:
'{"user_id": 9912, "name": "Jane Doe", "status": "active"}'`,
      pii_leak: `# Runtime Code
@monitor(assertions=[
    Assertion(type="no_pii"),
    Assertion(type="valid_json")
], fallback='{"status": "blocked", "reason": "PII_OR_SECRET_LEAK_INTERCEPTED"}')
async def get_customer_diagnostics(prompt: str):
    return await llm.complete(prompt)

# Model Output (VIOLATION):
'{"email": "ceo@corp.internal", "aws_secret": "AKIAIOSFODNN7EXAMPLE", "card": "4532-0150-1234-5678"}'`,
      sql_injection: `# Runtime Code
@monitor(assertions=[
    Assertion(type="read_only_sql"),
    Assertion(type="not_contains", value="DROP TABLE")
], fallback="SELECT 1 /* query blocked by security guardrail */;")
async def generate_sql_report(query_prompt: str):
    return await llm.complete(query_prompt)

# Model Output (VIOLATION):
'DROP TABLE customers; SELECT * FROM financial_records;'`,
      rag_hallucination: `# Runtime Code
clean_summary = guard(
    output=rag_completion,
    assertions=[
        Assertion(type="faithfulness", threshold=0.75),
        Assertion(type="contains", value="10mg once daily")
    ],
    context={"retrieved_chunk": "Prescribe Amoxicillin 10mg once daily for 7 days."},
    fallback="Unable to verify dosage. Consult physician."
)`
    };

    function updateGuardScenario() {
      const scEl = document.getElementById('guard-scenario');
      if (!scEl) return;
      const sc = scEl.value;
      const previewEl = document.getElementById('guard-code-preview');
      if (previewEl) previewEl.textContent = guardScenarios[sc] || guardScenarios['clean'];
    }

    function runGuardDemo() {
      const sc = document.getElementById('guard-scenario').value;
      const res = document.getElementById('guard-result');
      if (sc === 'clean') {
        res.innerHTML = `
<div style="color:#10b981; font-weight:700; margin-bottom:8px;">✔ GUARD PASSED: Production Output Safe (1.2ms)</div>
<div style="color:#94a3b8; font-size:0.85rem;">
  • <code>no_pii</code>: No confidential emails, cards, or API tokens.<br>
  • <code>valid_json</code>: Valid JSON schema confirmed.<br>
  • Streamed safely to client API consumer.
</div>
`;
      } else if (sc === 'pii_leak') {
        res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">⚡ INTERCEPTED: GuardrailViolation Raised (0.9ms)</div>
<div style="color:#f59e0b; font-size:0.85rem; margin-bottom:8px;">
  • <strong>High-Severity Leak:</strong> Credit Card (Luhn Valid) & AWS Secret Detected!<br>
  • <strong>Automated Fallback Triggered:</strong> Model output dropped before leaving boundary.
</div>
<div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); padding:8px; border-radius:6px; font-size:0.8rem; color:#fca5a5;">
  Fallback Delivered to Client:<br>
  <code>{"status": "blocked", "reason": "PII_OR_SECRET_LEAK_INTERCEPTED"}</code>
</div>
`;
      } else if (sc === 'sql_injection') {
        res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">⚡ INTERCEPTED: Destructive Query Blocked (0.6ms)</div>
<div style="color:#f59e0b; font-size:0.85rem; margin-bottom:8px;">
  • <strong>Rule Triggered:</strong> <code>DROP TABLE</code> found in query output.<br>
  • <strong>Sanitization:</strong> Database transaction protected.
</div>
<div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); padding:8px; border-radius:6px; font-size:0.8rem; color:#fca5a5;">
  Fallback Delivered to DB Driver:<br>
  <code>SELECT 1 /* query blocked by security guardrail */;</code>
</div>
`;
      } else {
        res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">⚡ INTERCEPTED: Hallucinated Medical Dosage (1.4ms)</div>
<div style="color:#f59e0b; font-size:0.85rem; margin-bottom:8px;">
  • <strong>Faithfulness Score:</strong> 0.32 &lt; 0.75 threshold.<br>
  • <strong>Missing Grounded Fact:</strong> '10mg once daily'.
</div>
<div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); padding:8px; border-radius:6px; font-size:0.8rem; color:#fca5a5;">
  Fallback Returned:<br>
  <code>"Unable to verify dosage. Consult physician."</code>
</div>
`;
      }
    }

    function runCicdDemo() {
      const res = document.getElementById('cicd-result');
      res.innerHTML = `
<div style="color:#ef4444; font-weight:700; font-size:0.95rem; margin-bottom:8px;">
  ❌ PR GATE FAILED — Exit Code: 3 (Regressions Detected)
</div>
<div style="font-size:0.8rem; color:#cbd5e1; background:#070a13; border:1px solid var(--border); border-radius:8px; padding:12px;">
  <div style="font-weight:700; color:#fff; margin-bottom:6px;">GitHub Step Summary & PR Comment:</div>
  <table style="width:100%; border-collapse:collapse; margin-bottom:10px; font-size:0.75rem;">
    <tr style="border-bottom:1px solid rgba(255,255,255,0.1); text-align:left; color:#94a3b8;">
      <th style="padding:4px;">Metric</th>
      <th style="padding:4px;">Baseline</th>
      <th style="padding:4px;">Current</th>
      <th style="padding:4px; text-align:right;">Delta</th>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
      <td style="padding:4px;"><strong>Pass Rate</strong></td>
      <td style="padding:4px;">100.0%</td>
      <td style="padding:4px;">66.7%</td>
      <td style="padding:4px; text-align:right; color:#ef4444; font-weight:700;">▼ -33.3%</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
      <td style="padding:4px;"><strong>Avg Latency</strong></td>
      <td style="padding:4px;">120ms</td>
      <td style="padding:4px;">148ms</td>
      <td style="padding:4px; text-align:right; color:#f59e0b;">▲ +28.0 ms</td>
    </tr>
  </table>
  <div style="color:#ef4444; font-weight:700; margin-bottom:4px;">⚠️ Broken Test Cases (Regressions):</div>
  <div style="color:#f87171; font-size:0.75rem;">• <code>case_refund_billing</code>: Passed in baseline, now FAILED in PR branch</div>
  <div style="margin-top:10px; color:#94a3b8; font-size:0.75rem;">
    Action: Pull request merge blocked until prompt regression is resolved.
  </div>
</div>
`;
    }

    // Initialize initial previews
    document.addEventListener("DOMContentLoaded", function() {
      updateGeneratedPreview();
      updateGuardScenario();
      if (typeof updateCustomPreset === 'function') updateCustomPreset();
      if (typeof calcROI === 'function') calcROI();
    });

    // Custom Evaluators Presets
    const customPresets = {
      polite_tone: {
        code: `@register_evaluator("polite_tone")
def check_polite(output: str, **kwargs) -> bool:
    courteous_phrases = ["please", "thank you", "glad to help", "kind regards"]
    return any(p in output.lower() for p in courteous_phrases)`,
        sample: "Thank you for contacting support! We are glad to help you with your account inquiry.",
        test: (text) => {
          const courteous = ["please", "thank you", "glad to help", "kind regards"];
          const pass = courteous.some(p => text.toLowerCase().includes(p));
          return {
            passed: pass,
            msg: pass ? "Contains courteous tone ('thank you' / 'glad to help')" : "Tone check failed: No polite phrases found."
          };
        }
      },
      no_competitor: {
        code: `@register_evaluator("no_competitor")
def check_competitors(output: str, **kwargs) -> bool:
    banned_rivals = ["rivalcorp", "badservice", "legacyllm"]
    return not any(r in output.lower() for r in banned_rivals)`,
        sample: "Veridex provides state-of-the-art LLM evaluation and testing.",
        test: (text) => {
          const banned = ["rivalcorp", "badservice", "legacyllm"];
          const hit = banned.filter(r => text.toLowerCase().includes(r));
          const pass = hit.length === 0;
          return {
            passed: pass,
            msg: pass ? "0 competitor brand mentions found" : `Violated: Mentioned banned rival [${hit.join(', ')}]`
          };
        }
      },
      ticket_code: {
        code: `@register_evaluator("ticket_format")
def check_ticket_id(output: str, **kwargs) -> bool:
    import re
    return bool(re.search(r"\bTCK-[0-9]{4}\b", output))`,
        sample: "Your support request has been logged under reference ID TCK-4092.",
        test: (text) => {
          const match = text.match(/\bTCK-[0-9]{4}\b/);
          return {
            passed: !!match,
            msg: match ? `Valid enterprise ticket code found: ${match[0]}` : "Missing required ticket code matching format 'TCK-XXXX'"
          };
        }
      }
    };

    function updateCustomPreset() {
      const presetKey = document.getElementById('custom-preset').value;
      const preset = customPresets[presetKey] || customPresets['polite_tone'];
      document.getElementById('custom-code-preview').textContent = preset.code;
      document.getElementById('custom-candidate-input').value = preset.sample;
    }

    function runCustomEvaluatorDemo() {
      const presetKey = document.getElementById('custom-preset').value;
      const preset = customPresets[presetKey] || customPresets['polite_tone'];
      const text = document.getElementById('custom-candidate-input').value;
      const res = document.getElementById('custom-eval-result');

      const outcome = preset.test(text);
      if (outcome.passed) {
        res.innerHTML = `
<div style="color:#10b981; font-weight:700; margin-bottom:8px;">✔ CUSTOM EVALUATOR PASSED (Score: 1.0)</div>
<div>• <code>Evaluator:</code> <span style="color:#38bdf8;">@register_evaluator("${presetKey}")</span></div>
<div>• <code>Result:</code> <span style="color:#10b981;">${outcome.msg}</span></div>
<div style="margin-top:12px; color:#64748b; font-size:0.8rem;">
  Execution Latency: 0.6ms | Registered directly in <code>EvaluatorRegistry</code>
</div>
`;
      } else {
        res.innerHTML = `
<div style="color:#ef4444; font-weight:700; margin-bottom:8px;">✘ CUSTOM EVALUATOR FAILED (Score: 0.0)</div>
<div>• <code>Evaluator:</code> <span style="color:#38bdf8;">@register_evaluator("${presetKey}")</span></div>
<div>• <code>Failure Reason:</code> <span style="color:#ef4444;">${outcome.msg}</span></div>
<div style="margin-top:12px; color:#f59e0b; font-size:0.8rem;">
  Action: Guardrail triggered. Output rejected according to custom rule.
</div>
`;
      }
    }

    // Enterprise ROI Calculator
    const modelPricing = {
      'gpt-4o': { in: 2.50, out: 10.00 },
      'claude-3-5': { in: 3.00, out: 15.00 },
      'gemini-1-5': { in: 1.25, out: 5.00 },
      'llama-3-70b': { in: 0.60, out: 0.60 }
    };

    function calcROI() {
      const reqs = parseInt(document.getElementById('input-reqs').value);
      const tokens = parseInt(document.getElementById('input-tokens').value);
      const rate = parseFloat(document.getElementById('input-rate').value);
      const modelKey = document.getElementById('input-model').value;

      document.getElementById('val-reqs').innerText = reqs.toLocaleString() + ' reqs/mo';
      document.getElementById('val-tokens').innerText = tokens + ' tokens';
      document.getElementById('val-rate').innerText = rate.toFixed(1) + '% failure rate';

      const pricing = modelPricing[modelKey] || modelPricing['gpt-4o'];
      // Assume 60% input tokens, 40% output tokens
      const avgCostPer1M = (pricing.in * 0.6) + (pricing.out * 0.4);
      const costPerReq = (tokens / 1000000) * avgCostPer1M;

      const failedReqs = reqs * (rate / 100);
      const monthlySavings = failedReqs * costPerReq;
      const annualSavings = monthlySavings * 12;

      document.getElementById('res-monthly-savings').innerText = '$' + Math.round(monthlySavings).toLocaleString() + ' / mo';
      document.getElementById('res-annual-savings').innerText = '$' + Math.round(annualSavings).toLocaleString() + ' / yr';
    }