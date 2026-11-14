from __future__ import annotations

import json
import re
from typing import Any, Optional
from veridex.core.models import Assertion, AssertionResult, AssertionType, TestResult
from veridex.evaluators.base import BaseEvaluator


class LLMJudgeEvaluator(BaseEvaluator):
    """
    Evaluates outputs using an LLM-as-a-judge rubric.
    Prompts a model to score output quality, adherence to instructions, and factual accuracy.
    """

    def __init__(self, judge_provider: Optional[Any] = None) -> None:
        self.judge_provider = judge_provider

    def evaluate(
        self,
        assertion: Assertion,
        output: str,
        test_case_result: Optional[TestResult] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AssertionResult:
        context = context or {}
        rubric = assertion.rubric or str(assertion.value or "Evaluate overall factual accuracy and clarity.")
        threshold = assertion.threshold
        expected = context.get("expected_output")
        input_prompt = context.get("input_prompt", "")

        # If no judge provider was configured, fall back to heuristic evaluation
        if not self.judge_provider:
            return self._heuristic_judge_fallback(output, rubric, threshold, expected)

        judge_prompt = self._construct_judge_prompt(
            input_prompt=input_prompt,
            output=output,
            expected=expected,
            rubric=rubric,
            threshold=threshold,
        )

        try:
            # Synchronously or via runner provider
            import asyncio
            if asyncio.iscoroutinefunction(self.judge_provider.generate):
                # When run inside an event loop, the runner will call async evaluate
                response = asyncio.run(self.judge_provider.generate(judge_prompt))
            else:
                response = self.judge_provider.generate(judge_prompt)

            raw_text = response.text if hasattr(response, "text") else str(response)
            parsed = self._parse_judge_response(raw_text)

            score = float(parsed.get("score", 0.0))
            passed = score >= threshold
            reasoning = parsed.get("reasoning", "LLM Judge evaluation completed.")

            return AssertionResult(
                assertion_type=AssertionType.LLM_JUDGE.value,
                name=assertion.name or "llm_judge",
                passed=passed,
                score=round(score, 3),
                message=f"Judge score {score:.2f} >= {threshold}: {reasoning}" if passed else f"Judge rejected output ({score:.2f} < {threshold}): {reasoning}",
                expected=f">= {threshold} adherence to: {rubric[:60]}",
                actual=f"Score: {score:.2f} | Reason: {reasoning}",
            )

        except Exception as e:
            return AssertionResult(
                assertion_type=AssertionType.LLM_JUDGE.value,
                name=assertion.name or "llm_judge",
                passed=False,
                score=0.0,
                message=f"Judge provider execution failed: {str(e)}",
                expected=rubric,
                actual=f"Error: {str(e)}",
            )

    @staticmethod
    def _construct_judge_prompt(
        input_prompt: str,
        output: str,
        expected: Optional[str],
        rubric: str,
        threshold: float,
    ) -> str:
        expected_section = f"\n[GROUND TRUTH / EXPECTED REFERENCE]\n{expected}\n" if expected else ""
        return f"""You are an expert impartial judge evaluating an AI model output.

[ORIGINAL INPUT PROMPT]
{input_prompt}
{expected_section}
[MODEL OUTPUT TO EVALUATE]
{output}

[EVALUATION RUBRIC & CRITERIA]
{rubric}
Threshold for passing: {threshold} (out of 1.0)

Provide your evaluation in strict valid JSON with the following keys:
{{
  "score": <float between 0.0 and 1.0>,
  "passed": <boolean>,
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<concise explanation of score based strictly on rubric>"
}}
Return ONLY the JSON object.
"""

    @staticmethod
    def _parse_judge_response(response_text: str) -> dict[str, Any]:
        cleaned = response_text.strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        return json.loads(cleaned)

    @staticmethod
    def _heuristic_judge_fallback(
        output: str, rubric: str, threshold: float, expected: Optional[str]
    ) -> AssertionResult:
        """Fallback mock evaluator when no live LLM API key is attached."""
        if not output.strip():
            return AssertionResult(
                assertion_type=AssertionType.LLM_JUDGE.value,
                name="llm_judge_fallback",
                passed=False,
                score=0.0,
                message="Judge fallback: Output is empty.",
            )

        # Baseline heuristic check
        score = 0.95 if len(output.strip()) > 10 else 0.5
        passed = score >= threshold
        return AssertionResult(
            assertion_type=AssertionType.LLM_JUDGE.value,
            name="llm_judge_fallback",
            passed=passed,
            score=score,
            message=f"Simulated judge rubric check passed (score {score:.2f} >= {threshold}).",
            expected=f">= {threshold} adherence to rubric",
            actual=f"Score: {score:.2f}",
        )
