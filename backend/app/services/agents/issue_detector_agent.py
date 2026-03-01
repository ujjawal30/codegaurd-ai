"""
CodeGuard AI — Issue Detector Agent.

Uses Gemini LLM to detect code issues grounded in both
deterministic metrics and RAG-retrieved best-practice standards.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.analysis import (
    DetectedIssue,
    FileClassification,
    RAGContext,
    ToolResults,
)
from app.services.agents.llm_client import get_chat_model, invoke_with_retry
from app.utils.guardrails import parse_llm_output_list, build_json_schema_prompt

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert Python code reviewer. Analyze the provided code metrics,
linting results, security scan results, and best-practice standards to identify code issues.

CRITICAL RULES:
1. Every issue MUST be grounded in either a metric threshold violation OR a best-practice standard.
2. Include the specific metric or standard in the "grounding" field.
3. Be specific about file paths and line numbers when available.
4. Categorize issues accurately: performance, security, maintainability, style, architecture, error_handling, testing.
5. Assign severity based on real impact: critical (security/data loss), high (bugs/major perf), medium (code quality), low (style/minor).
6. Provide actionable suggestions, not vague advice.

{schema_prompt}

Respond with a JSON array of detected issues."""


async def detect_issues(
    tool_results: ToolResults,
    classifications: list[FileClassification],
    rag_context: list[RAGContext],
) -> list[DetectedIssue]:
    """
    Detect code issues using LLM analysis grounded in metrics and standards.

    Args:
        tool_results: Results from all deterministic analysis tools.
        classifications: File classification results.
        rag_context: Retrieved best-practice standards.

    Returns:
        List of DetectedIssue objects with grounding citations.
    """
    model = get_chat_model(temperature=0.0)

    # ── Build context for the prompt ─────────────────────────────
    metrics_summary = _build_metrics_summary(tool_results)
    standards_summary = _build_standards_summary(rag_context)
    classifications_summary = _build_classifications_summary(classifications)

    schema_prompt = build_json_schema_prompt(DetectedIssue)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(schema_prompt=schema_prompt)),
        HumanMessage(content=f"""Analyze this Python codebase for issues:

## File Classifications
{classifications_summary}

## Static Analysis Metrics
{metrics_summary}

## Best-Practice Standards
{standards_summary}

Identify all significant issues. Ground each one in specific metrics or standards above."""),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        issues = parse_llm_output_list(raw_response, DetectedIssue)

        logger.info("issues_detected", count=len(issues))
        return issues

    except Exception as e:
        logger.error("issue_detection_failed", error=str(e))
        # Fallback: generate issues from tool results directly
        return _fallback_issues(tool_results)


def _build_metrics_summary(tool_results: ToolResults) -> str:
    """Build a readable summary of all tool results for the LLM."""
    sections = []

    # AST summary
    for path, ast in tool_results.ast_results.items():
        funcs = [f"{fn.name}(complexity={fn.complexity})" for fn in ast.functions]
        sections.append(f"**{path}**: {ast.total_lines} lines, functions: {funcs}")

    # Radon summary
    for path, radon in tool_results.radon_results.items():
        sections.append(
            f"**{path}**: CC={radon.cyclomatic_complexity} ({radon.complexity_rank}), "
            f"MI={radon.maintainability_index}, SLOC={radon.sloc}"
        )

    # Ruff issues
    for path, issues in tool_results.ruff_results.items():
        if issues:
            issue_codes = [f"{i.code}@L{i.line}" for i in issues[:10]]
            sections.append(f"**{path}** ruff: {issue_codes}")

    # Bandit issues
    for path, issues in tool_results.bandit_results.items():
        if issues:
            issue_descs = [f"{i.test_id}({i.severity.value})@L{i.line_range}" for i in issues]
            sections.append(f"**{path}** bandit: {issue_descs}")

    return "\n".join(sections) if sections else "No significant metrics found."


def _build_standards_summary(rag_context: list[RAGContext]) -> str:
    """Build a summary of RAG-retrieved standards."""
    if not rag_context:
        return "No standards retrieved."
    return "\n\n".join(
        f"### {ctx.title} [{ctx.category}]\n{ctx.content[:500]}"
        for ctx in rag_context
    )


def _build_classifications_summary(classifications: list[FileClassification]) -> str:
    """Build a summary of file classifications."""
    if not classifications:
        return "No classifications available."
    return "\n".join(
        f"- {clf.file_path}: {clf.role.value} (confidence={clf.confidence})"
        for clf in classifications
    )


def _fallback_issues(tool_results: ToolResults) -> list[DetectedIssue]:
    """Generate basic issues from tool results when LLM fails."""
    issues = []

    # Flag high-complexity functions
    for path, radon in tool_results.radon_results.items():
        if radon.cyclomatic_complexity > 10:
            issues.append(DetectedIssue(
                file_path=path,
                category="maintainability",
                severity="high",
                title=f"High cyclomatic complexity in {path}",
                description=f"Average cyclomatic complexity is {radon.cyclomatic_complexity} (rank {radon.complexity_rank})",
                suggestion="Refactor complex functions by extracting helper functions and reducing branching.",
                grounding=f"Radon CC={radon.cyclomatic_complexity}, threshold=10",
            ))

    # Flag security issues from bandit
    for path, bandit_issues in tool_results.bandit_results.items():
        for bi in bandit_issues:
            if bi.severity.value in ("high", "critical"):
                issues.append(DetectedIssue(
                    file_path=path,
                    line_range=bi.line_range,
                    category="security",
                    severity=bi.severity.value,
                    title=f"Security issue {bi.test_id} in {path}",
                    description=bi.issue_text,
                    suggestion="Review and remediate the security finding.",
                    grounding=f"Bandit {bi.test_id} severity={bi.severity.value}",
                ))

    return issues
