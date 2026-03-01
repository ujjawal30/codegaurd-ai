"""
CodeGuard AI — Radon Metrics Service.

Computes cyclomatic complexity, maintainability index, and raw LOC metrics
using the radon library's Python API (no subprocess).
"""

from radon.complexity import cc_visit, cc_rank
from radon.metrics import mi_visit
from radon.raw import analyze as radon_raw_analyze

from app.core.logging import get_logger
from app.schemas.analysis import RadonMetrics

logger = get_logger(__name__)


def _average_complexity(blocks: list) -> float:
    """Compute average cyclomatic complexity across all blocks."""
    if not blocks:
        return 0.0
    total = sum(block.complexity for block in blocks)
    return round(total / len(blocks), 2)


def _worst_rank(blocks: list) -> str:
    """Get the worst (highest) complexity rank across all blocks."""
    if not blocks:
        return "A"
    ranks = [cc_rank(block.complexity) for block in blocks]
    rank_order = ["A", "B", "C", "D", "E", "F"]
    worst_idx = max(rank_order.index(r) for r in ranks)
    return rank_order[worst_idx]


def analyze_file(file_path: str, content: str) -> RadonMetrics:
    """
    Compute Radon metrics for a single Python file.

    Args:
        file_path: Relative path of the file.
        content: Full source code content.

    Returns:
        RadonMetrics with complexity, maintainability, and LOC data.
    """
    # ── Cyclomatic complexity ────────────────────────────────────
    try:
        blocks = cc_visit(content)
        avg_complexity = _average_complexity(blocks)
        rank = _worst_rank(blocks)
    except Exception as e:
        logger.warning("radon_cc_failed", file=file_path, error=str(e))
        avg_complexity = 0.0
        rank = "A"

    # ── Maintainability index ────────────────────────────────────
    try:
        mi_score = mi_visit(content, multi=True)
    except Exception as e:
        logger.warning("radon_mi_failed", file=file_path, error=str(e))
        mi_score = 100.0

    # ── Raw LOC metrics -──────────────────────────────────────────
    try:
        raw = radon_raw_analyze(content)
        loc = raw.loc
        sloc = raw.sloc
        comments = raw.comments
        blank = raw.blank
    except Exception as e:
        logger.warning("radon_raw_failed", file=file_path, error=str(e))
        lines = content.count("\n") + 1
        loc = lines
        sloc = lines
        comments = 0
        blank = 0

    return RadonMetrics(
        file_path=file_path,
        cyclomatic_complexity=avg_complexity,
        maintainability_index=round(mi_score, 2),
        loc=loc,
        sloc=sloc,
        comments=comments,
        blank_lines=blank,
        complexity_rank=rank,
    )


async def analyze_files(files: list[dict]) -> dict[str, RadonMetrics]:
    """
    Analyze multiple Python files with Radon.

    Args:
        files: List of dicts with 'path' and 'content' keys.

    Returns:
        Dict mapping file path to RadonMetrics result.
    """
    results = {}
    for f in files:
        path = f["path"]
        content = f["content"]
        try:
            results[path] = analyze_file(path, content)
        except Exception as e:
            logger.error("radon_analysis_failed", file=path, error=str(e))
            results[path] = RadonMetrics(file_path=path)
    return results
