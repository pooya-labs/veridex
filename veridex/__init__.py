"""
Veridex: Production-grade LLM evaluation, regression testing, and reliability harness.
"""

from veridex.core.models import (
    Assertion,
    AssertionResult,
    AssertionType,
    SuiteResult,
    TestCase,
    TestResult,
    TestSuite,
)
from veridex.core.runner import TestRunner
from veridex.core.diff import SuiteComparator, RegressionDiff
from veridex.loaders.yaml_loader import SuiteLoader
from veridex.evaluators import EvaluatorRegistry
from veridex.providers import get_provider, BaseProvider, MockProvider

__version__ = "0.1.0"
__author__ = "Pooya Goodarzi"

__all__ = [
    "Assertion",
    "AssertionResult",
    "AssertionType",
    "SuiteResult",
    "TestCase",
    "TestResult",
    "TestSuite",
    "TestRunner",
    "SuiteComparator",
    "RegressionDiff",
    "SuiteLoader",
    "EvaluatorRegistry",
    "get_provider",
    "BaseProvider",
    "MockProvider",
    "__version__",
]
