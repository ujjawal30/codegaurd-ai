"""
CodeGuard AI — LangGraph Pipeline Orchestration.

Central state graph that wires all analysis stages together:
Extract → Static Analysis → Classify → RAG Retrieve → Detect Issues →
Generate Roadmap → Generate Tests → Validate.

Each node updates PipelineState and persists progress to the database.
"""

import os
import uuid
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.schemas.analysis import (
    AnalysisResponse,
    ExtractedFile,
    ToolResults,
    FileClassification,
    RAGContext,
    DetectedIssue,
    RefactorRoadmap,
    GeneratedTest,
    ValidationResult,
)

logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════
# Pipeline State
# ═════════════════════════════════════════════════════════════════

# ── TypedDict definitions ──────────────────────────────────────────

class _RequiredPipelineState(TypedDict):
    """Keys that must always be present in pipeline state."""

    job_id: str
    zip_path: str
    filename: str

class PipelineState(_RequiredPipelineState, total=False):
    """Typed state flowing through the LangGraph pipeline.

    Most keys are optional because they are populated incrementally as the
    pipeline advances.  The required base class ensures the core identifiers
    can be accessed without excessive type assertions.
    """

    # Stage 0: Extraction
    files: list[ExtractedFile]

    # Stage 1: Static Analysis
    tool_results: ToolResults

    # Stage 2: Classification
    file_classifications: list[FileClassification]

    # Stage 3: RAG
    rag_context: list[RAGContext]

    # Stage 4: Issue Detection
    detected_issues: list[DetectedIssue]

    # Stage 5: Generation
    refactor_roadmap: RefactorRoadmap
    generated_tests: list[GeneratedTest]

    # Stage 6: Validation
    validation_result: ValidationResult
    validation_attempts: int

    # Meta
    current_stage: str
    errors: list[str]


# ═════════════════════════════════════════════════════════════════
# Database Status Updates
# ═════════════════════════════════════════════════════════════════

async def _update_job_status(
    job_id: str,
    status: AnalysisStatus,
    stage: str | None = None,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    """Update the analysis job status in the database."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        stmt = select(AnalysisJob).where(AnalysisJob.id == uuid.UUID(job_id))
        db_result = await session.execute(stmt)
        job = db_result.scalar_one_or_none()

        if job:
            job.status = status
            if stage:
                job.current_stage = stage
            if result:
                job.result = result
            if error:
                job.error_message = error

            await session.commit()


# ═════════════════════════════════════════════════════════════════
# Pipeline Node Functions
# ═════════════════════════════════════════════════════════════════

async def extract_files(state: PipelineState) -> dict[str, Any]:
    """Stage 0: Extract Python files from the uploaded zip."""
    from app.utils.zip_handler import extract_python_files

    job_id = state["job_id"]
    zip_path = state["zip_path"]

    logger.info("pipeline_stage_start", job_id=job_id, stage="extract")
    await _update_job_status(job_id, AnalysisStatus.EXTRACTING, "extract")

    try:
        files = await extract_python_files(zip_path)
        logger.info("extraction_complete", job_id=job_id, file_count=len(files))
        return {"files": files, "current_stage": "extract"}
    except Exception as e:
        logger.error("extraction_failed", job_id=job_id, error=str(e))
        return {"files": [], "errors": [f"Extraction failed: {e}"], "current_stage": "extract"}


async def run_static_analysis(state: PipelineState) -> dict[str, Any]:
    """Stage 1: Run all deterministic analysis tools."""
    from app.services.tools.tool_orchestrator import run_all_tools

    job_id = state["job_id"]
    files = state.get("files", [])

    logger.info("pipeline_stage_start", job_id=job_id, stage="static_analysis")
    await _update_job_status(job_id, AnalysisStatus.ANALYZING, "static_analysis")

    if not files:
        return {"tool_results": ToolResults(), "current_stage": "static_analysis"}

    tool_results = await run_all_tools(files)
    return {"tool_results": tool_results, "current_stage": "static_analysis"}


async def classify_files(state: PipelineState) -> dict[str, Any]:
    """Stage 2: Classify files by architectural role using LLM."""
    from app.services.agents.classifier_agent import classify_files as do_classify

    job_id = state["job_id"]
    files = state.get("files", [])
    ast_results = state.get("tool_results", ToolResults()).ast_results

    logger.info("pipeline_stage_start", job_id=job_id, stage="classify")
    await _update_job_status(job_id, AnalysisStatus.CLASSIFYING, "classify")

    file_data = [{"path": f.path, "content": f.content} for f in files]
    classifications = await do_classify(file_data, ast_results)
    return {"file_classifications": classifications, "current_stage": "classify"}


async def retrieve_standards(state: PipelineState) -> dict[str, Any]:
    """Stage 3: Retrieve best-practice standards from RAG corpus."""
    from app.services.agents.rag_service import retrieve_standards as do_retrieve

    job_id = state["job_id"]
    classifications = state.get("file_classifications", [])

    logger.info("pipeline_stage_start", job_id=job_id, stage="rag_retrieve")
    await _update_job_status(job_id, AnalysisStatus.RETRIEVING, "rag_retrieve")

    async with AsyncSessionLocal() as session:
        rag_context = await do_retrieve(session, classifications)
    return {"rag_context": rag_context, "current_stage": "rag_retrieve"}


async def detect_issues(state: PipelineState) -> dict[str, Any]:
    """Stage 4: Detect issues grounded in metrics and standards."""
    from app.services.agents.issue_detector_agent import detect_issues as do_detect

    job_id = state["job_id"]
    tool_results = state.get("tool_results", ToolResults())
    classifications = state.get("file_classifications", [])
    rag_context = state.get("rag_context", [])

    logger.info("pipeline_stage_start", job_id=job_id, stage="detect_issues")
    await _update_job_status(job_id, AnalysisStatus.DETECTING, "detect_issues")

    issues = await do_detect(tool_results, classifications, rag_context)
    return {"detected_issues": issues, "current_stage": "detect_issues"}


async def generate_roadmap(state: PipelineState) -> dict[str, Any]:
    """Stage 5a: Generate prioritized refactoring roadmap."""
    from app.services.agents.roadmap_generator_agent import generate_roadmap as do_generate

    job_id = state["job_id"]
    issues = state.get("detected_issues", [])
    classifications = state.get("file_classifications", [])
    tool_results = state.get("tool_results", ToolResults())

    logger.info("pipeline_stage_start", job_id=job_id, stage="generate_roadmap")
    await _update_job_status(job_id, AnalysisStatus.GENERATING_ROADMAP, "generate_roadmap")

    roadmap = await do_generate(issues, classifications, tool_results)
    return {"refactor_roadmap": roadmap, "current_stage": "generate_roadmap"}


async def generate_tests(state: PipelineState) -> dict[str, Any]:
    """Stage 5b: Generate pytest tests for risky functions."""
    from app.services.agents.test_generator_agent import generate_tests as do_generate

    job_id = state["job_id"]
    tool_results = state.get("tool_results", ToolResults())
    issues = state.get("detected_issues", [])
    files = state.get("files", [])

    logger.info("pipeline_stage_start", job_id=job_id, stage="generate_tests")
    await _update_job_status(job_id, AnalysisStatus.GENERATING_TESTS, "generate_tests")

    file_data = [{"path": f.path, "content": f.content} for f in files]
    tests = await do_generate(tool_results, issues, file_data)
    return {"generated_tests": tests, "current_stage": "generate_tests"}


async def validate_output(state: PipelineState) -> dict[str, Any]:
    """Stage 6: Validate the full pipeline output."""
    from app.services.agents.validation_agent import validate_output as do_validate

    job_id = state["job_id"]
    issues = state.get("detected_issues", [])
    roadmap = state.get("refactor_roadmap", RefactorRoadmap(tasks=[], summary="", estimated_total_effort=""))
    tests = state.get("generated_tests", [])
    attempts = state.get("validation_attempts", 0)

    logger.info("pipeline_stage_start", job_id=job_id, stage="validate", attempt=attempts + 1)
    await _update_job_status(job_id, AnalysisStatus.VALIDATING, "validate")

    validation = await do_validate(issues, roadmap, tests)
    return {
        "validation_result": validation,
        "validation_attempts": attempts + 1,
        "current_stage": "validate",
    }


async def finalize(state: PipelineState) -> dict[str, Any]:
    """Final node: build response, persist results, and cleanup."""
    job_id = state["job_id"]

    logger.info("pipeline_finalizing", job_id=job_id)

    # Build the final response
    response = AnalysisResponse(
        job_id=job_id,
        filename=state.get("filename", ""),
        status="completed",
        file_count=len(state.get("files", [])),
        tool_results=state.get("tool_results", ToolResults()),
        file_classifications=state.get("file_classifications", []),
        rag_context=state.get("rag_context", []),
        detected_issues=state.get("detected_issues", []),
        refactor_roadmap=state.get("refactor_roadmap"),
        generated_tests=state.get("generated_tests", []),
        validation_result=state.get("validation_result"),
        summary=_build_summary(state),
    )

    # Persist to database
    result_dict = response.model_dump(mode="json")
    await _update_job_status(
        job_id,
        AnalysisStatus.COMPLETED,
        stage="completed",
        result=result_dict,
    )

    # Cleanup zip file
    zip_path = state.get("zip_path", "")
    if zip_path and os.path.exists(zip_path):
        try:
            os.unlink(zip_path)
        except OSError:
            pass

    logger.info("pipeline_complete", job_id=job_id)
    return {"current_stage": "completed"}


# ═════════════════════════════════════════════════════════════════
# Conditional Edge: Retry validation or finish
# ═════════════════════════════════════════════════════════════════

def should_retry_or_finish(state: PipelineState) -> str:
    """
    Decide whether to retry generation or proceed to finalization.

    Retries if validation failed and we haven't exceeded max attempts.
    """
    validation = state.get("validation_result")
    attempts = state.get("validation_attempts", 0)

    if validation and not validation.is_valid and attempts < 2:
        logger.info(
            "validation_retry",
            attempt=attempts,
            issues=validation.issues_found,
        )
        return "retry"
    return "finish"


# ═════════════════════════════════════════════════════════════════
# Summary Builder
# ═════════════════════════════════════════════════════════════════

def _build_summary(state: PipelineState) -> str:
    """Build a human-readable summary of the analysis."""
    files = state.get("files", [])
    issues = state.get("detected_issues", [])
    roadmap = state.get("refactor_roadmap")
    tests = state.get("generated_tests", [])
    validation = state.get("validation_result")

    parts = [f"Analyzed {len(files)} Python files."]

    if issues:
        severity_counts = {}
        for i in issues:
            sev = i.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        parts.append(f"Found {len(issues)} issues: {severity_counts}.")

    if roadmap and roadmap.tasks:
        parts.append(f"Generated {len(roadmap.tasks)} refactoring tasks.")

    if tests:
        parts.append(f"Generated {len(tests)} unit tests.")

    if validation:
        status = "passed" if validation.is_valid else "needs review"
        parts.append(f"Validation: {status} (confidence: {validation.confidence_score:.0%}).")

    return " ".join(parts)


# ═════════════════════════════════════════════════════════════════
# Graph Construction
# ═════════════════════════════════════════════════════════════════

def build_pipeline() -> CompiledStateGraph[PipelineState]:
    """
    Build and compile the LangGraph pipeline.

    Returns a compiled StateGraph ready to be invoked with PipelineState.
    """
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("extract", extract_files)
    graph.add_node("static_analysis", run_static_analysis)
    graph.add_node("classify", classify_files)
    graph.add_node("rag_retrieve", retrieve_standards)
    graph.add_node("detect_issues", detect_issues)
    graph.add_node("generate_roadmap", generate_roadmap)
    graph.add_node("generate_tests", generate_tests)
    graph.add_node("validate", validate_output)
    graph.add_node("finalize", finalize)

    # Add edges (linear pipeline with conditional validation retry)
    graph.set_entry_point("extract")
    graph.add_edge("extract", "static_analysis")
    graph.add_edge("static_analysis", "classify")
    graph.add_edge("classify", "rag_retrieve")
    graph.add_edge("rag_retrieve", "detect_issues")
    graph.add_edge("detect_issues", "generate_roadmap")
    graph.add_edge("generate_roadmap", "generate_tests")
    graph.add_edge("generate_tests", "validate")

    # Conditional: retry generation or finalize
    graph.add_conditional_edges(
        "validate",
        should_retry_or_finish,
        {
            "retry": "detect_issues",  # Re-run from issue detection
            "finish": "finalize",
        },
    )

    graph.add_edge("finalize", END)

    return graph.compile()


# Module-level compiled pipeline (reused across requests)
pipeline = build_pipeline()


async def run_pipeline(
    job_id: str,
    zip_path: str,
    filename: str,
) -> AnalysisResponse | None:
    """
    Execute the full analysis pipeline.

    Args:
        job_id: Unique analysis job ID.
        zip_path: Path to the uploaded zip file.
        filename: Original filename.

    Returns:
        The final AnalysisResponse, or None if pipeline failed.
    """
    initial_state: PipelineState = {
        "job_id": job_id,
        "zip_path": zip_path,
        "filename": filename,
        "files": [],
        "tool_results": ToolResults(),
        "file_classifications": [],
        "rag_context": [],
        "detected_issues": [],
        "refactor_roadmap": RefactorRoadmap(tasks=[], summary="", estimated_total_effort=""),
        "generated_tests": [],
        "validation_result": ValidationResult(
            is_valid=False, confidence_score=0, issues_found=[], suggestions=[], summary=""
        ),
        "validation_attempts": 0,
        "current_stage": "starting",
        "errors": [],
    }

    try:
        logger.info("pipeline_starting", job_id=job_id, filename=filename)
        final_state = await pipeline.ainvoke(initial_state)

        # Return the persisted result from the finalize step
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            stmt = select(AnalysisJob).where(AnalysisJob.id == uuid.UUID(job_id))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if job and job.result:
                return AnalysisResponse.model_validate(job.result)

        return None

    except Exception as e:
        logger.error("pipeline_failed", job_id=job_id, error=str(e))
        await _update_job_status(
            job_id,
            AnalysisStatus.FAILED,
            error=str(e),
        )
        return None
