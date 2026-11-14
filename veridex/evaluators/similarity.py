from __future__ import annotations

import re
from typing import Any, Optional, Set
from veridex.core.models import Assertion, AssertionResult, AssertionType, TestResult
from veridex.evaluators.base import BaseEvaluator


class SimilarityEvaluator(BaseEvaluator):
    """Evaluates text similarity using Levenshtein distance, Jaccard index, and token overlap."""

    def evaluate(
        self,
        assertion: Assertion,
        output: str,
        test_case_result: Optional[TestResult] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AssertionResult:
        context = context or {}
        a_type = assertion.type
        target = str(assertion.value if assertion.value is not None else context.get("expected_output", ""))
        threshold = assertion.threshold

        if a_type == AssertionType.LEVENSHTEIN_SIMILARITY:
            score = self._levenshtein_ratio(output.strip(), target.strip())
            passed = score >= threshold
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or f"levenshtein(th={threshold})",
                passed=passed,
                score=round(score, 4),
                message=f"Levenshtein similarity {score:.3f} >= {threshold}" if passed else f"Levenshtein similarity {score:.3f} < threshold {threshold}",
                expected=f">= {threshold}",
                actual=round(score, 4),
            )

        elif a_type == AssertionType.JACCARD_SIMILARITY:
            score = self._jaccard_similarity(output, target)
            passed = score >= threshold
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or f"jaccard(th={threshold})",
                passed=passed,
                score=round(score, 4),
                message=f"Jaccard index {score:.3f} >= {threshold}" if passed else f"Jaccard index {score:.3f} < threshold {threshold}",
                expected=f">= {threshold}",
                actual=round(score, 4),
            )

        elif a_type == AssertionType.TOKEN_OVERLAP:
            f1, prec, rec = self._token_f1(output, target)
            passed = f1 >= threshold
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or f"token_f1(th={threshold})",
                passed=passed,
                score=round(f1, 4),
                message=f"Token overlap F1={f1:.3f} (P={prec:.2f}, R={rec:.2f})" if passed else f"Token overlap F1 {f1:.3f} < threshold {threshold}",
                expected=f">= {threshold}",
                actual=round(f1, 4),
            )

        raise ValueError(f"Unsupported similarity assertion type: {a_type}")

    @staticmethod
    def _levenshtein_ratio(s1: str, s2: str) -> float:
        """Computes normalized Levenshtein similarity in range [0.0, 1.0]."""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        len1, len2 = len(s1), len(s2)
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,      # deletion
                    dp[i][j - 1] + 1,      # insertion
                    dp[i - 1][j - 1] + cost # substitution
                )

        distance = dp[len1][len2]
        max_len = max(len1, len2)
        return max(0.0, 1.0 - (distance / max_len))

    @classmethod
    def _tokenize(cls, text: str) -> Set[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        return set(words)

    @classmethod
    def _jaccard_similarity(cls, text1: str, text2: str) -> float:
        s1 = cls._tokenize(text1)
        s2 = cls._tokenize(text2)
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        intersection = len(s1.intersection(s2))
        union = len(s1.union(s2))
        return intersection / union if union > 0 else 0.0

    @classmethod
    def _token_f1(cls, prediction: str, ground_truth: str) -> tuple[float, float, float]:
        pred_tokens = re.findall(r"\b\w+\b", prediction.lower())
        gold_tokens = re.findall(r"\b\w+\b", ground_truth.lower())

        if not pred_tokens and not gold_tokens:
            return 1.0, 1.0, 1.0
        if not pred_tokens or not gold_tokens:
            return 0.0, 0.0, 0.0

        common: dict[str, int] = {}
        for token in pred_tokens:
            if token in gold_tokens:
                common[token] = common.get(token, 0) + 1

        num_same = sum(min(pred_tokens.count(k), gold_tokens.count(k)) for k in common)
        if num_same == 0:
            return 0.0, 0.0, 0.0

        precision = 1.0 * num_same / len(pred_tokens)
        recall = 1.0 * num_same / len(gold_tokens)
        f1 = (2 * precision * recall) / (precision + recall)
        return f1, precision, recall
