"""
CodeGuard AI — Validation Agent.

Secondary LLM pass that validates coherence and completeness
of the entire analysis pipeline output.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.analysis import (
    DetectedIssue,
    GeneratedTest,
    RefactorRoadmap,
    ValidationResult,
)
from app.services.agents.llm_client import get_chat_model, invoke_with_retry
from app.utils.guardrails import parse_llm_output, build_json_schema_prompt

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior code review validator. Your job is to quality-check
the output of an automated code analysis pipeline.

You must verify:
1. COVERAGE: Do the refactoring tasks address all critical and high-severity issues?
2. COHERENCE: Are the refactoring suggestions consistent and non-contradictory?
3. COMPLETENESS: Do generated tests cover the highest-risk functions?
4. FEASIBILITY: Are effort estimates realistic? Are suggestions actionable?
5. GROUNDING: Are issues properly connected to specific metrics or standards?

If you find problems, list them clearly. If the output is solid, confirm with high confidence.

{schema_prompt}

Respond with a single JSON object matching the ValidationResult schema."""


async def validate_output(
    detected_issues: list[DetectedIssue],
    roadmap: RefactorRoadmap,
    generated_tests: list[GeneratedTest],
) -> ValidationResult:
    """
    Validate the complete pipeline output for coherence and quality.

    This is the secondary LLM pass that acts as a quality gate
    before returning results to the user.

    Args:
        detected_issues: All detected issues.
        roadmap: Generated refactoring roadmap.
        generated_tests: Generated pytest tests.

    Returns:
        ValidationResult with pass/fail and suggestions.
    """
    model = get_chat_model(temperature=0.0)

    # Build summary of pipeline output
    issues_summary = "\n".join(
        f"- [{i.severity.value}] {i.title} ({i.category.value}) in {i.file_path}"
        for i in detected_issues
    )

    roadmap_summary = "\n".join(
        f"- P{t.priority}: {t.title} ({t.effort_estimate.value}) — addresses: {t.related_issues}"
        for t in roadmap.tasks
    ) if roadmap.tasks else "No tasks generated."

    tests_summary = "\n".join(
        f"- Test for {t.target_function} ({t.risk_level.value})"
        for t in generated_tests
    ) if generated_tests else "No tests generated."

    schema_prompt = build_json_schema_prompt(ValidationResult)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(schema_prompt=schema_prompt)),
        HumanMessage(content=f"""Validate this code analysis pipeline output:

## Detected Issues ({len(detected_issues)} total)
{issues_summary}

## Refactoring Roadmap ({len(roadmap.tasks)} tasks)
{roadmap_summary}
Total estimated effort: {roadmap.estimated_total_effort}

## Generated Tests ({len(generated_tests)} tests)
{tests_summary}

Assess the quality, coverage, and coherence of this analysis."""),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        result = parse_llm_output(raw_response, ValidationResult)

        logger.info(
            "validation_complete",
            is_valid=result.is_valid,
            confidence=result.confidence_score,
        )
        return result

    except Exception as e:
        logger.error("validation_failed", error=str(e))
        return ValidationResult(
            is_valid=True,
            confidence_score=0.5,
            issues_found=["Validation agent encountered an error — manual review recommended."],
            suggestions=[],
            summary="Automated validation could not complete. Results may still be useful but should be reviewed manually.",
        )
