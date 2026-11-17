"""
Veridex: Production-grade LLM evaluation, regression testing, and reliability harness.
"""

__version__ = "0.2.0"
__author__ = "Pooya Goodarzi"

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
from veridex.core.generator import SuiteGenerator
from veridex.core.html_reporter import HtmlReporter
from veridex.loaders.yaml_loader import SuiteLoader
from veridex.evaluators import EvaluatorRegistry, register_evaluator
from veridex.providers import get_provider, BaseProvider, MockProvider
from veridex.server import run_studio_server
from veridex.sdk import assert_eval
from veridex.integrations import (
    GuardrailViolation,
    guard,
    async_guard,
    monitor,
    VeridexCallbackHandler,
    VeridexTracer,
    VeridexSpan,
)

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
    "SuiteGenerator",
    "HtmlReporter",
    "SuiteLoader",
    "EvaluatorRegistry",
    "register_evaluator",
    "get_provider",
    "BaseProvider",
    "MockProvider",
    "run_studio_server",
    "assert_eval",
    "GuardrailViolation",
    "guard",
    "async_guard",
    "monitor",
    "VeridexCallbackHandler",
    "VeridexTracer",
    "VeridexSpan",
    "__version__",
]
