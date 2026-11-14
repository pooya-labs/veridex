import pytest
from veridex.core.models import Assertion, AssertionType, TestCase, TestSuite
from veridex.core.fuzzer import SuiteFuzzer


def test_suite_fuzzer_expansion():
    base_suite = TestSuite(
        id="base_test",
        name="Base Test",
        cases=[
            TestCase(
                id="c1",
                name="Case 1",
                prompt="Calculate total revenue for Q3.",
                assertions=[Assertion(type=AssertionType.VALID_JSON)],
            )
        ],
    )

    fuzzed = SuiteFuzzer.fuzz_suite(base_suite, modes=["typo", "noise", "adversarial"])
    # Original case + 3 fuzzed variants = 4 cases
    assert len(fuzzed.cases) == 4
    case_ids = [c.id for c in fuzzed.cases]
    assert "c1" in case_ids
    assert "c1_typo" in case_ids
    assert "c1_noise" in case_ids
    assert "c1_adversarial" in case_ids


def test_inject_typos():
    original = "The quick brown fox jumps over the lazy dog"
    typoed = SuiteFuzzer.inject_typos(original, rate=0.2)
    assert len(typoed) == len(original)
    assert isinstance(typoed, str)
