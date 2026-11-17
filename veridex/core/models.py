from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class AssertionType(str, enum.Enum):
    # Deterministic checks
    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    VALID_JSON = "valid_json"
    JSON_SCHEMA = "json_schema"
    MAX_LATENCY_MS = "max_latency_ms"
    MAX_TOKENS = "max_tokens"

    # Heuristic & Similarity checks
    LEVENSHTEIN_SIMILARITY = "levenshtein_similarity"
    JACCARD_SIMILARITY = "jaccard_similarity"
    TOKEN_OVERLAP = "token_overlap"

    # Safety & Guardrail checks
    NO_PII = "no_pii"
    NO_PROMPT_INJECTION = "no_prompt_injection"
    NO_JAILBREAK = "no_jailbreak"

    # Code & Syntax checks
    PYTHON_SYNTAX = "python_syntax"
    VALID_SQL = "valid_sql"
    SQL_SAFETY = "sql_safety"
    JSON_PATH = "json_path"

    # RAG & Groundedness checks
    FAITHFULNESS = "faithfulness"
    ANSWER_RELEVANCE = "answer_relevance"

    # Model-Assisted checks
    LLM_JUDGE = "llm_judge"


class Assertion(BaseModel):
    type: Union[AssertionType, str]
    value: Optional[Any] = None
    threshold: float = Field(default=1.0, ge=0.0)
    rubric: Optional[str] = None
    field_path: Optional[str] = None
    weight: float = Field(default=1.0, gt=0.0)
    name: Optional[str] = None

    @field_validator("type", mode="before")
    @classmethod
    def coerce_assertion_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return AssertionType(v)
            except ValueError:
                return v
        return v


class TestCase(BaseModel):
    __test__ = False
    id: str
    name: str
    description: Optional[str] = None
    prompt: str
    system_prompt: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    expected_output: Optional[str] = None
    assertions: List[Assertion] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TestSuite(BaseModel):
    __test__ = False
    id: str
    name: str
    description: Optional[str] = None
    provider: str = "mock"
    model: Optional[str] = None
    endpoint_url: Optional[str] = None
    matrix_models: List[str] = Field(default_factory=list)
    temperature: Optional[float] = 0.0
    max_tokens: Optional[int] = 1024
    system_prompt: Optional[str] = None
    cases: List[TestCase] = Field(default_factory=list)
    concurrency: int = Field(default=5, ge=1, le=50)
    timeout_seconds: float = Field(default=30.0, gt=0)


class AssertionResult(BaseModel):
    assertion_type: str
    name: Optional[str] = None
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None


class TestResult(BaseModel):
    __test__ = False
    case_id: str
    case_name: str
    passed: bool
    input_prompt: str
    system_prompt: Optional[str] = None
    output: str
    latency_ms: float = 0.0
    token_usage: Dict[str, int] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    assertion_results: List[AssertionResult] = Field(default_factory=list)
    error: Optional[str] = None


class SuiteResult(BaseModel):
    suite_id: str
    suite_name: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    provider: str
    model: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    average_latency_ms: float
    total_tokens: int
    total_cost_usd: float
    results: List[TestResult] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
