"""
CodeGuard AI — Ruff Linter Service.

Runs Ruff linting via subprocess and parses JSON output into structured results.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

from app.core.logging import get_logger
from app.schemas.analysis import RuffIssue, Severity

logger = get_logger(__name__)

# ── Severity mapping from Ruff rule prefixes ─────────────────────
# Ruff doesn't provide severity natively; we infer from rule category
SEVERITY_MAP: dict[str, Severity] = {
    "E": Severity.MEDIUM,    # pycodestyle errors
    "W": Severity.LOW,       # pycodestyle warnings
    "F": Severity.HIGH,      # pyflakes
    "B": Severity.HIGH,      # flake8-bugbear
    "C": Severity.LOW,       # conventions
    "D": Severity.LOW,       # docstrings
    "I": Severity.LOW,       # isort
    "N": Severity.LOW,       # naming
    "S": Severity.HIGH,      # bandit (security)
    "T": Severity.LOW,       # type checking
    "UP": Severity.LOW,      # pyupgrade
    "SIM": Severity.LOW,     # simplify
    "RUF": Severity.MEDIUM,  # ruff-specific
    "PL": Severity.MEDIUM,   # pylint
    "PERF": Severity.MEDIUM, # performance
}


def _get_severity(code: str) -> Severity:
    """Determine severity from ruff rule code."""
    # Try longest prefix first
    for prefix_len in [4, 3, 2, 1]:
        prefix = code[:prefix_len]
        if prefix in SEVERITY_MAP:
            return SEVERITY_MAP[prefix]
    return Severity.LOW


async def analyze_file(file_path: str, content: str) -> list[RuffIssue]:
    """
    Run Ruff on a single file's content and return structured issues.

    Creates a temporary file, runs ruff check with JSON output,
    and parses the results.

    Args:
        file_path: Original relative path (for reporting).
        content: Full source code content.

    Returns:
        List of RuffIssue objects.
    """
    issues: list[RuffIssue] = []

    # Write content to a temp file for ruff to analyze
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        logger.error("ruff_temp_file_failed", file=file_path, error=str(e))
        return issues

    try:
        proc = await asyncio.create_subprocess_exec(
            "ruff", "check", "--output-format=json",
            "--no-fix", "--no-cache",
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if stdout:
            raw_issues = json.loads(stdout.decode("utf-8", errors="replace"))
            for item in raw_issues:
                code = item.get("code", "UNKNOWN")
                issues.append(RuffIssue(
                    code=code,
                    message=item.get("message", ""),
                    line=item.get("location", {}).get("row", 0),
                    column=item.get("location", {}).get("column", 0),
                    severity=_get_severity(code),
                ))

    except asyncio.TimeoutError:
        logger.warning("ruff_timeout", file=file_path)
    except FileNotFoundError:
        logger.error("ruff_not_installed")
    except json.JSONDecodeError as e:
        logger.warning("ruff_json_parse_failed", file=file_path, error=str(e))
    except Exception as e:
        logger.error("ruff_failed", file=file_path, error=str(e))
    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return issues


async def analyze_files(files: list[dict]) -> dict[str, list[RuffIssue]]:
    """
    Run Ruff on multiple files concurrently.

    Args:
        files: List of dicts with 'path' and 'content' keys.

    Returns:
        Dict mapping file path to list of RuffIssue results.
    """
    results = {}
    tasks = []

    for f in files:
        path = f["path"]
        content = f["content"]
        tasks.append((path, analyze_file(path, content)))

    for path, task in tasks:
        try:
            results[path] = await task
        except Exception as e:
            logger.error("ruff_analysis_failed", file=path, error=str(e))
            results[path] = []

    return results
