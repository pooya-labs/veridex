from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from veridex.core.models import Assertion, AssertionResult, TestResult


class BaseEvaluator(ABC):
    """Abstract base class for all Veridex evaluators."""

    @abstractmethod
    def evaluate(
        self,
        assertion: Assertion,
        output: str,
        test_case_result: Optional[TestResult] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AssertionResult:
        """
        Evaluate an output against an assertion.

        Args:
            assertion: The assertion configuration.
            output: The LLM completion output string.
            test_case_result: Intermediate test result metadata (latency, cost, etc.).
            context: Optional contextual parameters (expected output, variables, etc.).

        Returns:
            AssertionResult with passed status, score (0.0-1.0), and diagnostic message.
        """
        pass
