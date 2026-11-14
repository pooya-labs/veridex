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
from veridex.core.matrix import MatrixRunner, MatrixResult
from veridex.core.fuzzer import SuiteFuzzer
from veridex.core.html_reporter import HtmlReporter
from veridex.loaders.yaml_loader import SuiteLoader
from veridex.evaluators import EvaluatorRegistry
from veridex.providers import get_provider, BaseProvider, MockProvider
from veridex.sdk import assert_eval

__version__ = "0.2.0"
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
    "MatrixRunner",
    "MatrixResult",
    "SuiteFuzzer",
    "HtmlReporter",
    "SuiteLoader",
    "EvaluatorRegistry",
    "get_provider",
    "BaseProvider",
    "MockProvider",
    "assert_eval",
    "__version__",
]
