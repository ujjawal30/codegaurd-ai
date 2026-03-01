"""
Tests for app.schemas.analysis — Pydantic model validation.
"""

import pytest
from app.schemas.analysis import (
    ExtractedFile,
    FunctionInfo,
    ClassInfo,
    ASTAnalysis,
    RadonMetrics,
    RuffIssue,
    BanditIssue,
    ToolResults,
    FileClassification,
    FileRole,
    Severity,
    IssueCategory,
    RAGContext,
    DetectedIssue,
    EffortEstimate,
    RefactorTask,
    RefactorRoadmap,
    RiskLevel,
    GeneratedTest,
    ValidationResult,
)


# ── ExtractedFile ───────────────────────────────────────────────


class TestExtractedFile:
    def test_valid_construction(self):
        f = ExtractedFile(path="app.py", content="print('hi')", size_bytes=11)
        assert f.path == "app.py"
        assert f.size_bytes == 11

    def test_negative_size_rejected(self):
        with pytest.raises(Exception):
            ExtractedFile(path="x.py", content="", size_bytes=-1)


# ── FunctionInfo / ClassInfo ────────────────────────────────────


class TestASTModels:
    def test_function_defaults(self):
        f = FunctionInfo(name="foo", lineno=1)
        assert f.is_async is False
        assert f.complexity >= 1
        assert f.args == []

    def test_class_with_methods(self):
        m = FunctionInfo(name="bar", lineno=5)
        c = ClassInfo(name="MyClass", lineno=1, methods=[m])
        assert len(c.methods) == 1
        assert c.methods[0].name == "bar"

    def test_ast_analysis_roundtrip(self):
        a = ASTAnalysis(
            file_path="test.py",
            functions=[FunctionInfo(name="f", lineno=1)],
            classes=[],
            imports=[],
            total_lines=10,
        )
        data = a.model_dump()
        restored = ASTAnalysis.model_validate(data)
        assert restored.file_path == "test.py"
        assert len(restored.functions) == 1


# ── Radon, Ruff, Bandit ────────────────────────────────────────


class TestToolModels:
    def test_radon_defaults(self):
        r = RadonMetrics(file_path="x.py")
        assert r.complexity_rank == "A"
        assert r.maintainability_index == 100.0

    def test_ruff_issue(self):
        issue = RuffIssue(code="E501", message="Line too long", line=10, column=80)
        assert issue.severity == Severity.LOW  # default

    def test_bandit_issue(self):
        issue = BanditIssue(
            test_id="B101", issue_text="Assert used", severity=Severity.LOW, confidence=Severity.HIGH
        )
        assert issue.test_id == "B101"

    def test_tool_results_empty(self):
        r = ToolResults()
        assert r.ast_results == {}
        assert r.radon_results == {}


# ── LLM Output Schemas ─────────────────────────────────────────


class TestLLMSchemas:
    def test_file_classification(self):
        fc = FileClassification(
            file_path="app.py",
            role=FileRole.CONTROLLER,
            confidence=0.9,
            reasoning="Handles HTTP routing",
        )
        assert fc.role == FileRole.CONTROLLER

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            FileClassification(
                file_path="x.py", role=FileRole.UTILITY, confidence=1.5, reasoning="test"
            )

    def test_rag_context(self):
        ctx = RAGContext(title="PEP8", category="style", content="Use 4 spaces.", relevance_score=0.85)
        assert ctx.relevance_score == 0.85

    def test_detected_issue(self):
        issue = DetectedIssue(
            title="SQL Injection",
            description="String interpolation in query",
            severity=Severity.CRITICAL,
            category=IssueCategory.SECURITY,
            file_path="app.py",
            line_range=[10, 12],
            suggestion="Use parameterized queries",
            grounding="Bandit B608: hardcoded SQL expression",
        )
        assert issue.severity == Severity.CRITICAL
        assert issue.category == IssueCategory.SECURITY

    def test_refactor_roadmap(self):
        task = RefactorTask(
            title="Fix SQL injection",
            description="Replace f-strings with parameterized queries",
            rationale="SQL injection is a critical security vulnerability",
            priority=1,
            effort_estimate=EffortEstimate.SMALL,
            affected_files=["app.py"],
        )
        roadmap = RefactorRoadmap(
            summary="Security fixes", tasks=[task], estimated_total_effort="2 hours"
        )
        assert len(roadmap.tasks) == 1

    def test_generated_test(self):
        t = GeneratedTest(
            target_file="app.py",
            target_function="get_user",
            test_code="def test_get_user(): ...",
            rationale="Tests SQL injection",
            risk_level=RiskLevel.CRITICAL,
        )
        assert t.target_function == "get_user"
        assert t.risk_level == RiskLevel.CRITICAL

    def test_validation_result(self):
        v = ValidationResult(
            is_valid=True,
            confidence_score=0.92,
            summary="Looks good",
            suggestions=["Add more tests"],
        )
        assert v.is_valid is True
        assert len(v.suggestions) == 1

    def test_roundtrip_detected_issue(self):
        issue = DetectedIssue(
            title="Test",
            description="Desc",
            severity=Severity.MEDIUM,
            category=IssueCategory.MAINTAINABILITY,
            file_path="x.py",
            line_range=[1],
            suggestion="Fix it",
            grounding="Radon CC > 10",
        )
        data = issue.model_dump()
        restored = DetectedIssue.model_validate(data)
        assert restored.title == "Test"
        assert restored.severity == Severity.MEDIUM
