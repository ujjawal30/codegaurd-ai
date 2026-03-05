"""
CodeGuard AI — File Classifier Agent.

Uses Gemini LLM to classify each Python file's architectural role
(controller, model, service, utility, config, test, etc.).

If the batch LLM call returns fewer classifications than files,
unclassified files are retried individually.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.analysis import (
    ASTAnalysis,
    FileClassification,
    FileRole,
)
from app.services.agents.llm_client import get_chat_model, invoke_with_retry
from app.utils.guardrails import parse_llm_output_list, parse_llm_output, build_json_schema_prompt

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert Python software architect. Your task is to classify
Python files by their architectural role in a codebase.

For each file, analyze the path, imports, class/function names, and structure to determine its role.

Possible roles:
- controller: API endpoints, route handlers, views
- model: Data models, ORM models, database schemas
- service: Business logic, domain services
- utility: Helper functions, shared utilities
- config: Configuration, settings, constants
- test: Test files, test utilities
- migration: Database migrations
- script: Standalone scripts, CLI tools
- other: Files that don't fit other categories

CRITICAL: You MUST return exactly one classification for EACH file provided.
If there are N files, you MUST respond with exactly N classification objects in your JSON array.

{schema_prompt}

Respond with a JSON array of classification objects. One for EACH file provided."""

SINGLE_FILE_PROMPT = """Classify this single Python file by its architectural role.

Possible roles: controller, model, service, utility, config, test, migration, script, other.

{schema_prompt}

Respond with a single JSON object (not an array) for this file."""


async def classify_files(
    files: list[dict],
    ast_results: dict[str, ASTAnalysis],
) -> list[FileClassification]:
    """
    Classify files by architectural role using Gemini LLM.

    Strategy:
      1. Send all files in one batch LLM call.
      2. If the LLM returns fewer classifications than files,
         retry unclassified files individually.
    """
    if not files:
        return []

    # ── Step 1: Batch classification ──────────────────────────────
    classifications = await _batch_classify(files, ast_results)
    classified_paths = {c.file_path for c in classifications}

    # ── Step 2: Retry missing files individually ─────────────────
    missing_files = [f for f in files if f["path"] not in classified_paths]
    if missing_files:
        logger.warning(
            "batch_classification_incomplete",
            total=len(files),
            classified=len(classifications),
            missing=len(missing_files),
        )
        for f in missing_files:
            single = await _classify_single_file(f, ast_results)
            if single:
                classifications.append(single)

    logger.info("files_classified", count=len(classifications), total=len(files))
    return classifications


async def _batch_classify(
    files: list[dict],
    ast_results: dict[str, ASTAnalysis],
) -> list[FileClassification]:
    """Classify all files in one LLM call."""
    model = get_chat_model(temperature=0.0)

    file_summaries = _build_file_summaries(files, ast_results)
    schema_prompt = build_json_schema_prompt(FileClassification)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(schema_prompt=schema_prompt)),
        HumanMessage(content=(
            f"Classify ALL {len(files)} Python files below. "
            f"You MUST return exactly {len(files)} classification objects.\n\n"
            + "\n---\n".join(file_summaries)
        )),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        classifications = parse_llm_output_list(raw_response, FileClassification)
        logger.info("batch_classified", count=len(classifications))
        return classifications
    except Exception as e:
        logger.error("batch_classification_failed", error=str(e))
        return []


async def _classify_single_file(
    file: dict,
    ast_results: dict[str, ASTAnalysis],
) -> FileClassification | None:
    """Classify a single file via individual LLM call."""
    model = get_chat_model(temperature=0.0)

    summaries = _build_file_summaries([file], ast_results)
    schema_prompt = build_json_schema_prompt(FileClassification)

    messages = [
        SystemMessage(content=SINGLE_FILE_PROMPT.format(schema_prompt=schema_prompt)),
        HumanMessage(content=f"Classify this file:\n\n{summaries[0]}"),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        classification = parse_llm_output(raw_response, FileClassification)
        logger.info("single_file_classified", path=file["path"], role=classification.role.value)
        return classification
    except Exception as e:
        logger.error("single_file_classification_failed", path=file["path"], error=str(e))
        return None


def _build_file_summaries(
    files: list[dict],
    ast_results: dict[str, ASTAnalysis],
) -> list[str]:
    """Build structured file summaries for the LLM prompt."""
    summaries = []
    for f in files:
        path = f["path"]
        content = f["content"]
        ast = ast_results.get(path)

        summary = f"### File: {path}\n"
        if ast:
            func_names = [fn.name for fn in ast.functions]
            class_names = [cls.name for cls in ast.classes]
            import_modules = [imp.module for imp in ast.imports]
            summary += f"Functions: {func_names}\n"
            summary += f"Classes: {class_names}\n"
            summary += f"Imports: {import_modules[:15]}\n"

        lines = content.split("\n")[:50]
        preview = "\n".join(lines)
        summary += f"Content preview:\n```python\n{preview}\n```\n"
        summaries.append(summary)

    return summaries
