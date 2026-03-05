"""
CodeGuard AI — Analysis Schemas.

Pydantic v2 models for all pipeline stage inputs/outputs.
These enforce structured LLM output validation.
"""

from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel, Field


# ═════════════════════════════════════════════════════════════════
# Stage 0: File Extraction
# ═════════════════════════════════════════════════════════════════

class ExtractedFile(BaseModel):
    """A single Python file extracted from the uploaded zip."""

    path: str = Field(..., description="Relative path within the repository")
    content: str = Field(..., description="Full file source code")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")


# ═════════════════════════════════════════════════════════════════
# Stage 1: Deterministic Analysis Results
# ═════════════════════════════════════════════════════════════════

class FunctionInfo(BaseModel):
    """Function-level AST analysis."""

    name: str
    lineno: int
    end_lineno: int | None = None
    args: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)
    docstring: str | None = None
    is_async: bool = False
    complexity: int = Field(default=1, ge=1, description="Estimated McCabe complexity")


class ClassInfo(BaseModel):
    """Class-level AST analysis."""

    name: str
    lineno: int
    end_lineno: int | None = None
    bases: list[str] = Field(default_factory=list)
    methods: list[FunctionInfo] = Field(default_factory=list)
    docstring: str | None = None


class ImportInfo(BaseModel):
    """Import statement details."""

    module: str
    names: list[str] = Field(default_factory=list)
    is_from_import: bool = False
    lineno: int = 0


class ASTAnalysis(BaseModel):
    """Complete AST analysis for a single file."""

    file_path: str
    functions: list[FunctionInfo] = Field(default_factory=list)
    classes: list[ClassInfo] = Field(default_factory=list)
    imports: list[ImportInfo] = Field(default_factory=list)
    total_lines: int = 0
    has_main_guard: bool = False


class RadonMetrics(BaseModel):
    """Radon static analysis metrics for a single file."""

    file_path: str
    cyclomatic_complexity: float = Field(default=0.0, ge=0)
    maintainability_index: float = Field(default=100.0)
    loc: int = Field(default=0, ge=0, description="Lines of code")
    sloc: int = Field(default=0, ge=0, description="Source lines of code")
    comments: int = Field(default=0, ge=0)
    blank_lines: int = Field(default=0, ge=0)
    complexity_rank: str = Field(default="A", description="A-F rating")


class Severity(str, enum.Enum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuffIssue(BaseModel):
    """A single Ruff linting issue."""

    code: str = Field(..., description="Rule code, e.g. E501")
    message: str
    line: int
    column: int
    severity: Severity = Severity.LOW


class BanditIssue(BaseModel):
    """A single Bandit security finding."""

    test_id: str = Field(..., description="Bandit test ID, e.g. B101")
    issue_text: str
    severity: Severity
    confidence: Severity
    line_range: list[int] = Field(default_factory=list)


class ToolResults(BaseModel):
    """Aggregated results from all deterministic analysis tools."""

    ast_results: dict[str, ASTAnalysis] = Field(default_factory=dict)
    radon_results: dict[str, RadonMetrics] = Field(default_factory=dict)
    ruff_results: dict[str, list[RuffIssue]] = Field(default_factory=dict)
    bandit_results: dict[str, list[BanditIssue]] = Field(default_factory=dict)


# ═════════════════════════════════════════════════════════════════
# Stage 2: File Classification (LLM)
# ═════════════════════════════════════════════════════════════════

class FileRole(str, enum.Enum):
    """Architectural role of a file."""

    CONTROLLER = "controller"
    MODEL = "model"
    SERVICE = "service"
    UTILITY = "utility"
    CONFIG = "config"
    TEST = "test"
    MIGRATION = "migration"
    SCRIPT = "script"
    OTHER = "other"


class FileClassification(BaseModel):
    """LLM classification of a file's architectural role."""

    file_path: str
    role: FileRole
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., max_length=2000)


# ═════════════════════════════════════════════════════════════════
# Stage 3: RAG Retrieval
# ═════════════════════════════════════════════════════════════════

class RAGContext(BaseModel):
    """A retrieved best-practice document from the RAG corpus."""

    title: str
    category: str
    content: str
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


# ═════════════════════════════════════════════════════════════════
# Stage 4: Issue Detection (LLM)
# ═════════════════════════════════════════════════════════════════

class IssueCategory(str, enum.Enum):
    """Categories of detected code issues."""

    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    ARCHITECTURE = "architecture"
    ERROR_HANDLING = "error_handling"
    TESTING = "testing"
    LOGIC_BUG = "logic_bug"


class DetectedIssue(BaseModel):
    """A code issue detected by the LLM, grounded in metrics and standards."""

    file_path: str
    line_range: list[int] = Field(default_factory=list, description="[start, end]")
    category: IssueCategory
    severity: Severity
    title: str = Field(..., max_length=200)
    description: str = Field(..., max_length=2000)
    suggestion: str = Field(..., max_length=2000)
    grounding: str = Field(
        ...,
        max_length=500,
        description="Citation of the metric or standard that triggered this issue",
    )


# ═════════════════════════════════════════════════════════════════
# Stage 5: Refactor Roadmap + Test Generation (LLM)
# ═════════════════════════════════════════════════════════════════

class EffortEstimate(str, enum.Enum):
    """Relative effort estimate for refactoring tasks."""

    TRIVIAL = "trivial"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    MAJOR = "major"


class RefactorTask(BaseModel):
    """A single refactoring task in the roadmap."""

    title: str = Field(..., max_length=200)
    priority: int = Field(..., ge=1, le=10, description="1 = highest priority")
    affected_files: list[str] = Field(default_factory=list)
    effort_estimate: EffortEstimate
    description: str = Field(..., max_length=2000)
    rationale: str = Field(..., max_length=2000)
    related_issues: list[str] = Field(
        default_factory=list,
        description="Titles of DetectedIssues this task addresses",
    )


class RefactorRoadmap(BaseModel):
    """Prioritized refactoring roadmap."""

    tasks: list[RefactorTask] = Field(default_factory=list)
    summary: str = Field(..., max_length=2000)
    estimated_total_effort: str = Field(
        ..., description="Human-readable total effort estimate"
    )


class RiskLevel(str, enum.Enum):
    """Risk level for functions needing tests."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GeneratedTest(BaseModel):
    """A generated pytest unit test for a risky function."""

    target_function: str = Field(..., description="Fully qualified function name")
    target_file: str
    test_code: str = Field(..., description="Complete pytest test code")
    rationale: str = Field(..., max_length=2000)
    risk_level: RiskLevel


# ═════════════════════════════════════════════════════════════════
# Stage 6: Validation (LLM)
# ═════════════════════════════════════════════════════════════════

class ValidationResult(BaseModel):
    """Result of the secondary LLM validation pass."""

    is_valid: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    issues_found: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    summary: str = Field(..., max_length=2000)


# ═════════════════════════════════════════════════════════════════
# Final Aggregate Response
# ═════════════════════════════════════════════════════════════════

class AnalysisResponse(BaseModel):
    """Complete dashboard-ready analysis response."""

    job_id: str
    filename: str
    status: str
    file_count: int

    # Stage 1
    tool_results: ToolResults

    # Stage 2
    file_classifications: list[FileClassification] = Field(default_factory=list)

    # Stage 3
    rag_context: list[RAGContext] = Field(default_factory=list)

    # Stage 4
    detected_issues: list[DetectedIssue] = Field(default_factory=list)

    # Stage 5
    refactor_roadmap: RefactorRoadmap | None = None
    generated_tests: list[GeneratedTest] = Field(default_factory=list)

    # Stage 6
    validation_result: ValidationResult | None = None

    # Meta
    summary: str = ""
