"""
CodeGuard AI — Test Generator Agent.

Uses Gemini LLM to generate pytest unit tests for functions
identified as high-risk (high complexity + security issues).
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.analysis import (
    ASTAnalysis,
    DetectedIssue,
    GeneratedTest,
    ToolResults,
)
from app.services.agents.llm_client import get_chat_model, invoke_with_retry
from app.utils.guardrails import parse_llm_output_list, build_json_schema_prompt

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert Python test engineer. Generate pytest unit tests
for functions identified as high-risk in the codebase.

RULES:
1. Generate valid, runnable pytest code
2. Follow the Arrange-Act-Assert pattern
3. Include edge cases: empty inputs, None values, boundary conditions
4. Mock external dependencies (database, network, file system)
5. Use descriptive test names: test_<function>_<scenario>_<expected>
6. Include appropriate imports in the test code
7. Add brief comments explaining each test case

{schema_prompt}

Respond with a JSON array of GeneratedTest objects."""


def _identify_risky_functions(
    tool_results: ToolResults,
    issues: list[DetectedIssue],
) -> list[dict]:
    """
    Identify high-risk functions that need testing.

    A function is risky if it has:
    - High cyclomatic complexity (>5)
    - Security issues in its line range
    - Error handling issues
    """
    risky = []

    for path, ast in tool_results.ast_results.items():
        for func in ast.functions:
            risk_reasons = []
            risk_level = "low"

            # Check complexity
            if func.complexity > 5:
                risk_reasons.append(f"complexity={func.complexity}")
                risk_level = "medium" if func.complexity <= 10 else "high"

            # Check for related security/error issues
            file_issues = [i for i in issues if i.file_path == path]
            for issue in file_issues:
                if issue.line_range and func.lineno:
                    if any(
                        func.lineno <= line <= (func.end_lineno or func.lineno + 100)
                        for line in issue.line_range
                    ):
                        risk_reasons.append(f"{issue.category.value}: {issue.title}")
                        if issue.severity.value in ("high", "critical"):
                            risk_level = "critical"

            if risk_reasons:
                risky.append({
                    "function": func.name,
                    "file": path,
                    "risk_level": risk_level,
                    "reasons": risk_reasons,
                    "args": func.args,
                    "is_async": func.is_async,
                    "lineno": func.lineno,
                })

        # Also check class methods
        for cls in ast.classes:
            for method in cls.methods:
                if method.complexity > 5:
                    risky.append({
                        "function": f"{cls.name}.{method.name}",
                        "file": path,
                        "risk_level": "medium" if method.complexity <= 10 else "high",
                        "reasons": [f"complexity={method.complexity}"],
                        "args": method.args,
                        "is_async": method.is_async,
                        "lineno": method.lineno,
                    })

    # Sort by risk level (critical > high > medium > low)
    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risky.sort(key=lambda x: risk_order.get(x["risk_level"], 4))

    return risky[:15]  # Limit to top 15 risky functions


async def generate_tests(
    tool_results: ToolResults,
    detected_issues: list[DetectedIssue],
    files: list[dict],
) -> list[GeneratedTest]:
    """
    Generate pytest tests for risky functions.

    Args:
        tool_results: Full tool analysis results.
        detected_issues: Detected code issues.
        files: Original file contents.

    Returns:
        List of GeneratedTest objects.
    """
    risky_functions = _identify_risky_functions(tool_results, detected_issues)

    if not risky_functions:
        logger.info("no_risky_functions_found")
        return []

    model = get_chat_model(temperature=0.3)

    # Build function context with source code
    function_context = []
    for rf in risky_functions:
        # Find the source file
        source = ""
        for f in files:
            if f["path"] == rf["file"]:
                source = f["content"]
                break

        function_context.append(
            f"### {rf['function']} in {rf['file']}\n"
            f"Risk: {rf['risk_level']} — {', '.join(rf['reasons'])}\n"
            f"Args: {rf['args']}, Async: {rf['is_async']}\n"
            f"Source file:\n```python\n{source[:2000]}\n```"
        )

    schema_prompt = build_json_schema_prompt(GeneratedTest)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(schema_prompt=schema_prompt)),
        HumanMessage(content=f"""Generate pytest tests for these {len(risky_functions)} risky functions:

{"--- ".join(function_context)}

Generate comprehensive tests for each function."""),
    ]

    try:
        raw_response = await invoke_with_retry(model, messages)
        tests = parse_llm_output_list(raw_response, GeneratedTest)

        logger.info("tests_generated", count=len(tests))
        return tests

    except Exception as e:
        logger.error("test_generation_failed", error=str(e))
        return []
