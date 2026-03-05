"""
CodeGuard AI — Issue Detector Agent.

Uses deterministic tool results as the foundation,
then enriches them with LLM analysis grounded in RAG standards.

Architecture: tool issues are ALWAYS included. LLM adds depth, not breadth.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.analysis import (
    DetectedIssue,
    FileClassification,
    RAGContext,
    ToolResults,
    IssueCategory,
    Severity
)
from app.services.agents.llm_client import get_chat_model, invoke_with_retry
from app.utils.guardrails import parse_llm_output_list, build_json_schema_prompt

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert Python code reviewer. You are given source code and static analysis
findings. Your job is to provide ADDITIONAL architectural and design-level issues beyond
what the static tools already found.

The tools already caught: unused imports, security vulnerabilities, complexity metrics.
You should focus on:
- Architectural problems (god classes, tight coupling, missing abstractions)
- Logic bugs visible in the source code
- Missing error handling patterns
- Performance anti-patterns
- Testing gaps

RULES:
1. Each issue MUST cite evidence in the "grounding" field.
2. Be specific: include file paths, line numbers, function names.
3. Category: security, performance, maintainability, style, architecture, error_handling, testing.
4. Severity: critical, high, medium, low.
5. Provide actionable suggestions.

{schema_prompt}

Respond with a JSON array of additional detected issues."""


async def detect_issues(
    tool_results: ToolResults,
    classifications: list[FileClassification],
    rag_context: list[RAGContext],
    files: list[dict] | None = None,
) -> list[DetectedIssue]:
    """
    Detect code issues by combining deterministic tool findings with LLM analysis.

    Strategy:
      1. ALWAYS generate issues directly from Bandit, Ruff, and Radon results.
      2. Then ask the LLM for additional architectural/design issues.
      3. Merge both sets — tools findings are never dropped.
    """
    # ── Step 1: Deterministic issues from tools (ALWAYS included) ─
    tool_issues = _issues_from_tools(tool_results)
    logger.info("tool_issues_generated", count=len(tool_issues))

    # ── Step 2: Enrich security suggestions with LLM (context-aware) ─
    tool_issues = await _enrich_security_suggestions(tool_issues, files)

    # ── Step 3: LLM enrichment for architectural insights ─────────
    llm_issues = await _llm_detect_issues(
        tool_results, classifications, rag_context, files
    )
    logger.info("llm_issues_detected", count=len(llm_issues))

    # ── Step 4: Merge (tool issues first, then LLM additions) ─────
    all_issues = tool_issues + llm_issues
    logger.info("total_issues", count=len(all_issues))
    return all_issues


async def _llm_detect_issues(
    tool_results: ToolResults,
    classifications: list[FileClassification],
    rag_context: list[RAGContext],
    files: list[dict] | None = None,
) -> list[DetectedIssue]:
    """Ask LLM for additional architectural/design issues."""
    model = get_chat_model(temperature=0.0)

    source_summary = _build_source_summary(files) if files else ""
    standards_summary = _build_standards_summary(rag_context)
    classifications_summary = _build_classifications_summary(classifications)

    schema_prompt = build_json_schema_prompt(DetectedIssue)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(schema_prompt=schema_prompt)),
        HumanMessage(content=f"""Analyze this Python codebase for ADDITIONAL issues
beyond what static tools already found:

## File Classifications
{classifications_summary}

## Source Code
{source_summary}

## Best-Practice Standards
{standards_summary}

Focus on architectural, design, and logic issues that static tools cannot detect.
Respond with a JSON array (can be empty if no additional issues found)."""),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        return parse_llm_output_list(raw_response, DetectedIssue)
    except Exception as e:
        logger.error("llm_issue_detection_failed", error=str(e))
        return []


# ═════════════════════════════════════════════════════════════════
# Deterministic issue generation from tool results
# ═════════════════════════════════════════════════════════════════

def _short_title(text: str) -> str:
    """Truncate issue text for use as a title."""
    return text[:80] + "..." if len(text) > 80 else text


def _issues_from_tools(tool_results: ToolResults) -> list[DetectedIssue]:
    """Generate DetectedIssue objects directly from tool results."""
    issues = []

    # ── Bandit security findings ──────────────────────────────────
    for path, bandit_issues in tool_results.bandit_results.items():
        for bi in bandit_issues:
            severity_map = {"low": Severity.LOW, "medium": Severity.MEDIUM, "high": Severity.HIGH, "critical": Severity.CRITICAL}
            issues.append(DetectedIssue(
                file_path=path,
                line_range=bi.line_range,
                category=IssueCategory.SECURITY,
                severity=severity_map.get(bi.severity.value, Severity.MEDIUM),
                title=f"Security: {bi.test_id} — {_short_title(bi.issue_text)}",
                description=bi.issue_text,
                suggestion="Pending...",  # Placeholder — enriched by LLM below
                grounding=f"Bandit {bi.test_id}: severity={bi.severity.value}, confidence={bi.confidence.value}",
            ))

    # ── Ruff linting issues ──────────────────────────────────────
    for path, ruff_issues in tool_results.ruff_results.items():
        for ri in ruff_issues:
            issues.append(DetectedIssue(
                file_path=path,
                line_range=[ri.line],
                category=IssueCategory.STYLE,
                severity=Severity.LOW,
                title=f"Lint: {ri.code} — {ri.message}",
                description=ri.message,
                suggestion=f"Remove or fix the issue at line {ri.line}.",
                grounding=f"Ruff {ri.code} at line {ri.line}",
            ))

    # ── Radon complexity issues ──────────────────────────────────
    for path, ast in tool_results.ast_results.items():
        for func in ast.functions:
            if func.complexity > 10:
                issues.append(DetectedIssue(
                    file_path=path,
                    line_range=[func.lineno, func.end_lineno or func.lineno],
                    category=IssueCategory.MAINTAINABILITY,
                    severity=Severity.HIGH,
                    title=f"High complexity: `{func.name}` (CC={func.complexity})",
                    description=(
                        f"Function `{func.name}` has cyclomatic complexity of {func.complexity}, "
                        f"which is above the recommended threshold of 10. This makes the function "
                        f"hard to test, understand, and maintain."
                    ),
                    suggestion=(
                        f"Refactor `{func.name}` by extracting helper functions, "
                        f"using early returns, or applying the strategy pattern to reduce branching."
                    ),
                    grounding=f"AST analysis: {func.name} complexity={func.complexity}, threshold=10",
                ))
            elif func.complexity > 5:
                issues.append(DetectedIssue(
                    file_path=path,
                    line_range=[func.lineno, func.end_lineno or func.lineno],
                    category=IssueCategory.MAINTAINABILITY,
                    severity=Severity.MEDIUM,
                    title=f"Moderate complexity: `{func.name}` (CC={func.complexity})",
                    description=(
                        f"Function `{func.name}` has cyclomatic complexity of {func.complexity}. "
                        f"Consider simplifying to improve readability."
                    ),
                    suggestion="Consider extracting complex conditions into named helper functions.",
                    grounding=f"AST analysis: {func.name} complexity={func.complexity}",
                ))

    # ── Low maintainability index ─────────────────────────────────
    for path, radon in tool_results.radon_results.items():
        if radon.maintainability_index < 50:
            issues.append(DetectedIssue(
                file_path=path,
                category=IssueCategory.MAINTAINABILITY,
                severity=Severity.HIGH,
                title=f"Low maintainability index: {radon.maintainability_index:.0f}/100",
                description=(
                    f"File {path} has a maintainability index of {radon.maintainability_index:.1f} "
                    f"(rank {radon.complexity_rank}). Scores below 50 indicate code that is "
                    f"very difficult to maintain."
                ),
                suggestion="Break down the file into smaller, focused modules with clear responsibilities.",
                grounding=f"Radon MI={radon.maintainability_index:.1f}, rank={radon.complexity_rank}",
            ))

    return issues


async def _enrich_security_suggestions(
    issues: list[DetectedIssue],
    files: list[dict] | None,
) -> list[DetectedIssue]:
    """
    Use LLM to generate context-aware suggestions for security findings.

    Sends all Bandit issues + relevant source code in one batched call.
    Falls back to generic suggestions if LLM fails.
    """
    security_issues = [i for i in issues if i.category == IssueCategory.SECURITY]
    if not security_issues:
        return issues

    # Build source snippets around each finding
    findings_context = []
    for idx, issue in enumerate(security_issues):
        snippet = _get_code_snippet(files, issue.file_path, issue.line_range)
        findings_context.append(
            f"Finding {idx + 1}: [{issue.grounding}]\n"
            f"File: {issue.file_path}, Lines: {issue.line_range}\n"
            f"Issue: {issue.description}\n"
            f"Code:\n```python\n{snippet}\n```"
        )

    model = get_chat_model(temperature=0.2)
    messages = [
        SystemMessage(content=(
            "You are a security engineer. For each Bandit finding below, provide a specific, "
            "actionable remediation suggestion based on the actual code shown. "
            "Include a corrected code snippet where possible.\n\n"
            "Respond with a JSON array of strings — one suggestion per finding, in the same order. "
            "Each suggestion should be 2-4 sentences with concrete steps."
        )),
        HumanMessage(content=f"Generate remediation for these {len(security_issues)} findings:\n\n"
                     + "\n---\n".join(findings_context)),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        json_str = _extract_json_array(raw_response)
        suggestions = json.loads(json_str)

        if isinstance(suggestions, list) and len(suggestions) == len(security_issues):
            sec_idx = 0
            for i, issue in enumerate(issues):
                if issue.category == IssueCategory.SECURITY and sec_idx < len(suggestions):
                    issues[i] = issue.model_copy(update={"suggestion": str(suggestions[sec_idx])})
                    sec_idx += 1
            logger.info("security_suggestions_enriched", count=len(suggestions))
        else:
            logger.warning("suggestion_count_mismatch", expected=len(security_issues), got=len(suggestions) if isinstance(suggestions, list) else 0)
            _apply_fallback_suggestions(issues)

    except Exception as e:
        logger.error("security_suggestion_enrichment_failed", error=str(e))
        _apply_fallback_suggestions(issues)

    return issues


def _apply_fallback_suggestions(issues: list[DetectedIssue]) -> None:
    """Apply static fallback suggestions for security issues that still have placeholder text."""
    fallback = {
        "B105": "Move secrets to environment variables or a secrets manager. Never hardcode credentials.",
        "B106": "Move passwords to environment variables. Use a secrets manager for production.",
        "B107": "Move passwords to environment variables. Use a secrets manager for production.",
        "B301": "Use `json.loads()` or `ast.literal_eval()` instead of `pickle.loads()`.",
        "B307": "Replace `eval()` with `ast.literal_eval()` or a proper expression parser.",
        "B324": "Replace MD5/SHA1 with `bcrypt`/`argon2` for passwords, `hashlib.sha256` for general hashing.",
        "B602": "Avoid `shell=True`. Use `subprocess.run(['cmd', 'arg1'], shell=False)` with a list.",
        "B603": "Validate all inputs before passing to subprocess. Use allowlists for commands.",
        "B608": "Use parameterized queries: `cursor.execute('SELECT ... WHERE id = ?', (id,))`.",
        "B404": "Avoid `shell=True`, validate inputs, and use allowlists for permitted commands.",
    }
    for i, issue in enumerate(issues):
        if issue.category == IssueCategory.SECURITY and issue.suggestion == "Pending...":
            test_id = issue.grounding.split(":")[0].replace("Bandit ", "").strip()
            suggestion = fallback.get(test_id, "Review and remediate. Consult OWASP guidelines.")
            issues[i] = issue.model_copy(update={"suggestion": suggestion})


def _get_code_snippet(
    files: list[dict] | None,
    file_path: str,
    line_range: list[int] | None,
    context_lines: int = 5,
) -> str:
    """Extract a code snippet around the issue lines."""
    if not files or not line_range:
        return "(source not available)"

    for f in files:
        if f["path"] == file_path:
            lines = f["content"].split("\n")
            start = max(0, line_range[0] - context_lines - 1)
            end = min(len(lines), (line_range[-1] if len(line_range) > 1 else line_range[0]) + context_lines)
            numbered = [f"{start + j + 1:>4} | {line}" for j, line in enumerate(lines[start:end])]
            return "\n".join(numbered)

    return "(file not found)"


def _extract_json_array(text: str) -> str:
    """Extract a JSON array from LLM response text."""
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    if "[" in text:
        start = text.index("[")
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return text.strip()


def _build_source_summary(files: list[dict] | None) -> str:
    """Include truncated source code for each file."""
    if not files:
        return "Source code not available."
    sections = []
    for f in files:
        code = f.get("content", "")
        if len(code) > 3000:
            code = code[:3000] + "\n# ... (truncated)"
        sections.append(f"### {f['path']}\n```python\n{code}\n```")
    return "\n\n".join(sections)


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
