"""
CodeGuard AI — File Classifier Agent.

Uses Gemini LLM to classify each Python file's architectural role
(controller, model, service, utility, config, test, etc.).
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
from app.utils.guardrails import parse_llm_output_list, build_json_schema_prompt

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

{schema_prompt}

Respond with a JSON array of classification objects. One for each file provided."""

async def classify_files(
    files: list[dict],
    ast_results: dict[str, ASTAnalysis],
) -> list[FileClassification]:
    """
    Classify files by architectural role using Gemini.

    Args:
        files: List of dicts with 'path' and 'content' keys.
        ast_results: AST analysis results for context.

    Returns:
        List of FileClassification objects.
    """
    if not files:
        return []

    model = get_chat_model(temperature=0.0)

    # Build file summaries for the prompt (truncate content for token budget)
    file_summaries = []
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

        # Include first 50 lines for context
        lines = content.split("\n")[:50]
        summary += f"Content preview:\n```python\n{'chr(10)'.join(lines)}\n```\n"
        file_summaries.append(summary)

    schema_prompt = build_json_schema_prompt(FileClassification)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(schema_prompt=schema_prompt)),
        HumanMessage(content=f"Classify these {len(files)} Python files:\n\n" + "\n---\n".join(file_summaries)),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        classifications = parse_llm_output_list(raw_response, FileClassification)

        logger.info("files_classified", count=len(classifications))
        return classifications

    except Exception as e:
        logger.error("classification_failed", error=str(e))
        # Fallback: heuristic-based classification
        return _fallback_classify(files)


def _fallback_classify(files: list[dict]) -> list[FileClassification]:
    """Heuristic fallback classification when LLM fails."""
    results = []
    for f in files:
        path = f["path"].lower()
        role = FileRole.OTHER
        if "test" in path:
            role = FileRole.TEST
        elif "model" in path or "schema" in path:
            role = FileRole.MODEL
        elif "config" in path or "settings" in path:
            role = FileRole.CONFIG
        elif "util" in path or "helper" in path:
            role = FileRole.UTILITY
        elif "service" in path:
            role = FileRole.SERVICE
        elif "api" in path or "route" in path or "endpoint" in path or "view" in path:
            role = FileRole.CONTROLLER
        elif "migration" in path or "alembic" in path:
            role = FileRole.MIGRATION

        results.append(FileClassification(
            file_path=f["path"],
            role=role,
            confidence=0.5,
            reasoning="Heuristic fallback classification based on file path.",
        ))
    return results
