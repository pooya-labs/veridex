from __future__ import annotations

import re
from typing import Any, List, Optional, Set
from veridex.core.models import Assertion, AssertionResult, AssertionType, TestResult
from veridex.evaluators.base import BaseEvaluator


class RagGroundednessEvaluator(BaseEvaluator):
    """
    Evaluates RAG faithfulness (groundedness in context) and answer relevance.
    Detects ungrounded hallucinated facts, entities, or outside claims.
    """

    STOPWORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
        "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
        "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
        "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
        "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
        "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
        "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she",
        "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
        "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until",
        "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
        "why", "will", "with", "you", "your", "yours", "yourself", "yourselves"
    }

    def evaluate(
        self,
        assertion: Assertion,
        output: str,
        test_case_result: Optional[TestResult] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AssertionResult:
        context = context or {}
        a_type = assertion.type
        threshold = assertion.threshold

        # Extract context text from variables or assertion value or metadata
        ref_context = (
            assertion.value
            or context.get("variables", {}).get("context")
            or context.get("expected_output")
            or ""
        )
        ref_context_str = str(ref_context)

        input_prompt = str(context.get("input_prompt", ""))

        if a_type == AssertionType.FAITHFULNESS:
            score, ungrounded = self._calculate_faithfulness(output, ref_context_str)
            passed = score >= threshold
            msg = (
                f"Faithfulness score {score:.2f} >= {threshold} (grounded in context)"
                if passed
                else f"Faithfulness score {score:.2f} < {threshold}. Potential ungrounded tokens/claims: {', '.join(ungrounded[:5])}"
            )
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or "rag_faithfulness",
                passed=passed,
                score=round(score, 3),
                message=msg,
                expected=f">= {threshold} grounded in reference context",
                actual=round(score, 3),
            )

        elif a_type == AssertionType.ANSWER_RELEVANCE:
            question_text = (
                str(assertion.value)
                if assertion.value
                else context.get("variables", {}).get("question")
            )
            if not question_text:
                q_match = re.search(r"Question:\s*[\"']?([^\"\n\r]+)[\"']?", input_prompt, re.IGNORECASE)
                question_text = q_match.group(1).strip() if q_match else input_prompt

            score = self._calculate_relevance(output, question_text)
            passed = score >= threshold
            return AssertionResult(
                assertion_type=a_type.value,
                name=assertion.name or "answer_relevance",
                passed=passed,
                score=round(score, 3),
                message=f"Answer relevance {score:.2f} >= {threshold}" if passed else f"Answer relevance {score:.2f} < {threshold} (missed question intent)",
                expected=f">= {threshold} relevance to prompt",
                actual=round(score, 3),
            )

        raise ValueError(f"Unsupported RAG assertion type: {a_type}")

    @classmethod
    def _extract_content_tokens(cls, text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", text.lower())
        return {w for w in words if w not in cls.STOPWORDS and len(w) > 1}

    @classmethod
    def _calculate_faithfulness(cls, answer: str, context: str) -> tuple[float, list[str]]:
        ans_tokens = cls._extract_content_tokens(answer)
        if not ans_tokens:
            return 1.0, []

        ctx_tokens = cls._extract_content_tokens(context)
        if not ctx_tokens:
            return 0.0, list(ans_tokens)

        # Check overlap
        grounded = ans_tokens.intersection(ctx_tokens)
        ungrounded = list(ans_tokens.difference(ctx_tokens))

        # Check numerical claims specifically (numbers must exist in context!)
        ans_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", answer))
        ctx_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", context))
        unsupported_numbers = ans_numbers.difference(ctx_numbers)

        score = len(grounded) / len(ans_tokens)
        if unsupported_numbers:
            # Penalize hallucinated numerical stats heavily
            score *= 0.5
            ungrounded = list(unsupported_numbers) + ungrounded

        return max(0.0, min(1.0, score)), ungrounded

    @classmethod
    def _calculate_relevance(cls, answer: str, question: str) -> float:
        q_tokens = cls._extract_content_tokens(question)
        if not q_tokens:
            return 1.0

        ans_tokens = cls._extract_content_tokens(answer)
        if not ans_tokens:
            return 0.0

        overlap = q_tokens.intersection(ans_tokens)
        return len(overlap) / len(q_tokens)
