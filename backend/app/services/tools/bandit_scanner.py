"""
CodeGuard AI — Bandit Security Scanner Service.

Runs Bandit security analysis via subprocess and parses JSON output
into structured results.
"""

import asyncio
import json
import os
import tempfile

from app.core.logging import get_logger
from app.schemas.analysis import BanditIssue, Severity

logger = get_logger(__name__)

# ── Severity mapping ────────────────────────────────────────────
BANDIT_SEVERITY_MAP: dict[str, Severity] = {
    "LOW": Severity.LOW,
    "MEDIUM": Severity.MEDIUM,
    "HIGH": Severity.HIGH,
    "CRITICAL": Severity.CRITICAL,
}


def _map_severity(level: str) -> Severity:
    """Map Bandit severity/confidence strings to our Severity enum."""
    return BANDIT_SEVERITY_MAP.get(level.upper(), Severity.LOW)


async def analyze_file(file_path: str, content: str) -> list[BanditIssue]:
    """
    Run Bandit on a single file's content and return structured issues.

    Creates a temporary file, runs bandit with JSON output,
    and parses the results.

    Args:
        file_path: Original relative path (for reporting).
        content: Full source code content.

    Returns:
        List of BanditIssue objects.
    """
    issues: list[BanditIssue] = []

    # Write content to a temp file for bandit to analyze
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
        logger.error("bandit_temp_file_failed", file=file_path, error=str(e))
        return issues

    try:
        proc = await asyncio.create_subprocess_exec(
            "bandit", "-f", "json",
            "--quiet",
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if stdout:
            raw_output = json.loads(stdout.decode("utf-8", errors="replace"))
            raw_results = raw_output.get("results", [])

            for item in raw_results:
                issues.append(BanditIssue(
                    test_id=item.get("test_id", "UNKNOWN"),
                    issue_text=item.get("issue_text", ""),
                    severity=_map_severity(item.get("issue_severity", "LOW")),
                    confidence=_map_severity(item.get("issue_confidence", "LOW")),
                    line_range=item.get("line_range", []),
                ))

    except asyncio.TimeoutError:
        logger.warning("bandit_timeout", file=file_path)
    except FileNotFoundError:
        logger.error("bandit_not_installed")
    except json.JSONDecodeError as e:
        logger.warning("bandit_json_parse_failed", file=file_path, error=str(e))
    except Exception as e:
        logger.error("bandit_failed", file=file_path, error=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return issues


async def analyze_files(files: list[dict]) -> dict[str, list[BanditIssue]]:
    """
    Run Bandit on multiple files concurrently.

    Args:
        files: List of dicts with 'path' and 'content' keys.

    Returns:
        Dict mapping file path to list of BanditIssue results.
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
            logger.error("bandit_analysis_failed", file=path, error=str(e))
            results[path] = []

    return results
