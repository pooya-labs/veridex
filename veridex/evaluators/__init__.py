from __future__ import annotations

from typing import Any, Dict, Optional
from veridex.core.models import Assertion, AssertionResult, AssertionType, TestResult
from veridex.evaluators.base import BaseEvaluator
from veridex.evaluators.deterministic import DeterministicEvaluator
from veridex.evaluators.similarity import SimilarityEvaluator
from veridex.evaluators.safety import SafetyEvaluator
from veridex.evaluators.judge import LLMJudgeEvaluator
from veridex.evaluators.code_and_sql import CodeAndSqlEvaluator
from veridex.evaluators.rag import RagGroundednessEvaluator


class EvaluatorRegistry:
    """Central registry and router for all evaluator types."""

    def __init__(self, judge_provider: Optional[Any] = None) -> None:
        self.deterministic = DeterministicEvaluator()
        self.similarity = SimilarityEvaluator()
        self.safety = SafetyEvaluator()
        self.code_sql = CodeAndSqlEvaluator()
        self.rag = RagGroundednessEvaluator()
        self.judge = LLMJudgeEvaluator(judge_provider=judge_provider)

    def evaluate(
        self,
        assertion: Assertion,
        output: str,
        test_case_result: Optional[TestResult] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AssertionResult:
        a_type = assertion.type

        if a_type in {
            AssertionType.EXACT_MATCH,
            AssertionType.CONTAINS,
            AssertionType.NOT_CONTAINS,
            AssertionType.REGEX,
            AssertionType.VALID_JSON,
            AssertionType.JSON_SCHEMA,
            AssertionType.MAX_LATENCY_MS,
            AssertionType.MAX_TOKENS,
        }:
            return self.deterministic.evaluate(assertion, output, test_case_result, context)

        elif a_type in {
            AssertionType.LEVENSHTEIN_SIMILARITY,
            AssertionType.JACCARD_SIMILARITY,
            AssertionType.TOKEN_OVERLAP,
        }:
            return self.similarity.evaluate(assertion, output, test_case_result, context)

        elif a_type in {
            AssertionType.NO_PII,
            AssertionType.NO_PROMPT_INJECTION,
        }:
            return self.safety.evaluate(assertion, output, test_case_result, context)

        elif a_type in {
            AssertionType.PYTHON_SYNTAX,
            AssertionType.VALID_SQL,
            AssertionType.SQL_SAFETY,
            AssertionType.JSON_PATH,
        }:
            return self.code_sql.evaluate(assertion, output, test_case_result, context)

        elif a_type in {
            AssertionType.FAITHFULNESS,
            AssertionType.ANSWER_RELEVANCE,
        }:
            return self.rag.evaluate(assertion, output, test_case_result, context)

        elif a_type == AssertionType.LLM_JUDGE:
            return self.judge.evaluate(assertion, output, test_case_result, context)

        raise ValueError(f"Unknown assertion type: {a_type}")


__all__ = [
    "BaseEvaluator",
    "DeterministicEvaluator",
    "SimilarityEvaluator",
    "SafetyEvaluator",
    "CodeAndSqlEvaluator",
    "RagGroundednessEvaluator",
    "LLMJudgeEvaluator",
    "EvaluatorRegistry",
]
