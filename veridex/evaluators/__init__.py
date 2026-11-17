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
    """Central registry and router for all evaluator types, with custom plugin support."""

    _custom_evaluators: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, evaluator: Any) -> None:
        """Register a custom evaluator function or BaseEvaluator subclass."""
        cls._custom_evaluators[name.lower()] = evaluator

    @classmethod
    def get_custom(cls, name: str) -> Optional[Any]:
        return cls._custom_evaluators.get(name.lower())

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
        type_str = a_type.value if hasattr(a_type, "value") else str(a_type)

        # Check custom evaluators first
        if type_str.lower() in self._custom_evaluators:
            custom_fn = self._custom_evaluators[type_str.lower()]
            if isinstance(custom_fn, type) and issubclass(custom_fn, BaseEvaluator):
                return custom_fn().evaluate(assertion, output, test_case_result, context)
            elif callable(custom_fn):
                try:
                    res = custom_fn(output=output, assertion=assertion, context=context)
                except TypeError:
                    res = custom_fn(output)

                if isinstance(res, AssertionResult):
                    return res
                passed = bool(res)
                return AssertionResult(
                    assertion_type=type_str,
                    passed=passed,
                    score=1.0 if passed else 0.0,
                    message="Custom evaluator passed" if passed else "Custom evaluator assertion failed",
                )

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
            AssertionType.NO_JAILBREAK,
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


def register_evaluator(name: str):
    """Decorator to register a custom evaluator with Veridex.

    Example:
        @register_evaluator("brand_voice")
        def check_brand(output: str, **kwargs) -> bool:
            return "Veridex" in output
    """
    def decorator(fn_or_cls: Any) -> Any:
        EvaluatorRegistry.register(name, fn_or_cls)
        return fn_or_cls
    return decorator


__all__ = [
    "BaseEvaluator",
    "DeterministicEvaluator",
    "SimilarityEvaluator",
    "SafetyEvaluator",
    "CodeAndSqlEvaluator",
    "RagGroundednessEvaluator",
    "LLMJudgeEvaluator",
    "EvaluatorRegistry",
    "register_evaluator",
]
