"""
CodeGuard AI — Refactor Roadmap Generator Agent.

Uses Gemini LLM to generate a prioritized refactoring roadmap
based on detected issues, file classifications, and metrics.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.analysis import (
    DetectedIssue,
    FileClassification,
    RefactorRoadmap,
    ToolResults,
)
from app.services.agents.llm_client import get_chat_model, invoke_with_retry
from app.utils.guardrails import parse_llm_output, build_json_schema_prompt

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert software architect creating a refactoring roadmap.

Given detected issues, file classifications, and code metrics, create a prioritized
refactoring plan that maximizes impact while minimizing risk.

PRIORITIZATION CRITERIA (use all three):
1. Severity: Critical/security issues first
2. Effort: Quick wins before major overhauls
3. Blast radius: Isolated changes before cross-cutting ones

RULES:
- Priority 1 = highest priority, 10 = lowest
- Each task must reference specific detected issues it addresses
- Effort estimates: trivial (<1h), small (<4h), medium (<1d), large (<1w), major (>1w)
- Group related issues into single tasks when they share the same root cause
- Provide a clear summary and realistic total effort estimate

{schema_prompt}

Respond with a single JSON object matching the RefactorRoadmap schema."""


async def generate_roadmap(
    detected_issues: list[DetectedIssue],
    classifications: list[FileClassification],
    tool_results: ToolResults,
) -> RefactorRoadmap:
    """
    Generate a prioritized refactoring roadmap.

    Args:
        detected_issues: All detected code issues.
        classifications: File role classifications.
        tool_results: Raw metrics from analysis tools.

    Returns:
        RefactorRoadmap with prioritized tasks.
    """
    model = get_chat_model(temperature=0.2)

    # Build issue summary
    issue_summary = "\n".join(
        f"- [{i.severity.value.upper()}] {i.title} in {i.file_path}: {i.description}"
        for i in detected_issues
    ) or "No issues were detected by the issue detection agent."

    # Build raw tool findings for additional context
    tool_findings = []
    for path, issues in tool_results.bandit_results.items():
        for bi in issues:
            tool_findings.append(f"- [BANDIT {bi.test_id}] {bi.severity.value}: {bi.issue_text} in {path} L{bi.line_range}")
    for path, radon in tool_results.radon_results.items():
        if radon.cyclomatic_complexity > 5:
            tool_findings.append(f"- [RADON] CC={radon.cyclomatic_complexity} ({radon.complexity_rank}) MI={radon.maintainability_index:.0f} in {path}")
    tool_summary = "\n".join(tool_findings) if tool_findings else "No significant tool findings."

    # Build file context
    file_context = "\n".join(
        f"- {clf.file_path} ({clf.role.value})"
        for clf in classifications
    )

    schema_prompt = build_json_schema_prompt(RefactorRoadmap)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(schema_prompt=schema_prompt)),
        HumanMessage(content=f"""Create a refactoring roadmap for this codebase:

## Detected Issues ({len(detected_issues)} total)
{issue_summary}

## Raw Tool Findings (security, complexity, linting — use these even if not all became detected issues)
{tool_summary}

## File Architecture
{file_context}

Generate a prioritized list of refactoring tasks that address ALL findings above — especially security issues."""),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        roadmap = parse_llm_output(raw_response, RefactorRoadmap)

        logger.info("roadmap_generated", task_count=len(roadmap.tasks))
        return roadmap

    except Exception as e:
        logger.error("roadmap_generation_failed", error=str(e))
        return RefactorRoadmap(
            tasks=[],
            summary="Roadmap generation failed. Please review detected issues manually.",
            estimated_total_effort="Unknown",
        )
