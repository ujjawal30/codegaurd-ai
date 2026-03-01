"""
CodeGuard AI — Tool Orchestrator.

Runs all deterministic analysis tools concurrently and merges results
into a single ToolResults object.
"""

import asyncio

from app.core.logging import get_logger
from app.schemas.analysis import ExtractedFile, ToolResults
from app.services.tools import ast_parser, radon_analyzer, ruff_linter, bandit_scanner

logger = get_logger(__name__)


async def run_all_tools(files: list[ExtractedFile]) -> ToolResults:
    """
    Execute all static analysis tools concurrently on the given files.

    Runs AST parsing, Radon metrics, Ruff linting, and Bandit scanning
    in parallel using asyncio.gather. Each tool failure is isolated —
    other tools continue even if one fails.

    Args:
        files: List of ExtractedFile objects to analyze.

    Returns:
        ToolResults containing merged results from all tools.
    """
    # Prepare file data as dicts for tool interfaces
    file_data = [{"path": f.path, "content": f.content} for f in files]

    logger.info("tool_orchestrator_starting", file_count=len(files))

    # Run all tools concurrently with isolated error handling
    ast_task = _safe_run("ast_parser", ast_parser.analyze_files(file_data))
    radon_task = _safe_run("radon_analyzer", radon_analyzer.analyze_files(file_data))
    ruff_task = _safe_run("ruff_linter", ruff_linter.analyze_files(file_data))
    bandit_task = _safe_run("bandit_scanner", bandit_scanner.analyze_files(file_data))

    ast_results, radon_results, ruff_results, bandit_results = await asyncio.gather(
        ast_task, radon_task, ruff_task, bandit_task,
    )

    logger.info(
        "tool_orchestrator_complete",
        ast_files=len(ast_results),
        radon_files=len(radon_results),
        ruff_files=len(ruff_results),
        bandit_files=len(bandit_results),
    )

    return ToolResults(
        ast_results=ast_results,
        radon_results=radon_results,
        ruff_results=ruff_results,
        bandit_results=bandit_results,
    )


async def _safe_run(tool_name: str, coro) -> dict:
    """
    Run a tool coroutine with error isolation.

    If the tool fails, logs the error and returns an empty dict
    so other tools aren't affected.
    """
    try:
        return await asyncio.wait_for(coro, timeout=120)
    except asyncio.TimeoutError:
        logger.error("tool_timeout", tool=tool_name)
        return {}
    except Exception as e:
        logger.error("tool_failed", tool=tool_name, error=str(e))
        return {}
