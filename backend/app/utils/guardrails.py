"""
CodeGuard AI — LLM Output Guardrails.

Wraps LLM calls with structured output parsing, validation, and retry logic.
Ensures reliability of the agentic pipeline.
"""

import json
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── Constants ────────────────────────────────────────────────────
MAX_LLM_RETRIES = 3
MAX_OUTPUT_TOKENS = 8192


class LLMOutputError(Exception):
    """Raised when LLM output cannot be parsed into the expected schema."""
    pass


def extract_json_from_response(text: str) -> str:
    """
    Extract JSON from LLM response text.

    Handles cases where LLM wraps JSON in markdown code blocks
    or includes extra text before/after the JSON.
    """
    # Try to find JSON in code blocks first
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()

    # Try to find raw JSON (object or array)
    for char, end_char in [("{", "}"), ("[", "]")]:
        if char in text:
            start = text.index(char)
            # Find the matching closing bracket
            depth = 0
            for i in range(start, len(text)):
                if text[i] == char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]

    return text.strip()


def parse_llm_output(raw_text: str, schema: Type[T]) -> T:
    """
    Parse and validate LLM output against a Pydantic schema.

    Args:
        raw_text: Raw text output from the LLM.
        schema: Pydantic model class to validate against.

    Returns:
        Validated Pydantic model instance.

    Raises:
        LLMOutputError: If parsing or validation fails.
    """
    try:
        json_str = extract_json_from_response(raw_text)
        data = json.loads(json_str)
        return schema.model_validate(data)
    except json.JSONDecodeError as e:
        logger.error(
            "json_parse_failed",
            error=str(e),
            raw_text_preview=raw_text[:200],
        )
        raise LLMOutputError(f"Failed to parse JSON: {e}") from e
    except ValidationError as e:
        logger.error(
            "schema_validation_failed",
            schema=schema.__name__,
            errors=e.error_count(),
            raw_text_preview=raw_text[:200],
        )
        raise LLMOutputError(
            f"Schema validation failed for {schema.__name__}: {e}"
        ) from e


def parse_llm_output_list(raw_text: str, item_schema: Type[T]) -> list[T]:
    """
    Parse LLM output as a list of Pydantic models.

    Args:
        raw_text: Raw text output from the LLM.
        item_schema: Pydantic model class for each list item.

    Returns:
        List of validated Pydantic model instances.

    Raises:
        LLMOutputError: If parsing or validation fails.
    """
    try:
        json_str = extract_json_from_response(raw_text)
        data = json.loads(json_str)
        if not isinstance(data, list):
            data = [data]
        return [item_schema.model_validate(item) for item in data]
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(
            "list_parse_failed",
            schema=item_schema.__name__,
            error=str(e),
        )
        raise LLMOutputError(f"Failed to parse list of {item_schema.__name__}: {e}") from e


def build_json_schema_prompt(schema: Type[BaseModel]) -> str:
    """
    Generate a prompt snippet describing the expected JSON schema.

    Used to instruct the LLM on the exact output format expected.
    """
    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    return (
        f"You MUST respond with valid JSON matching this exact schema:\n"
        f"```json\n{schema_json}\n```\n"
        f"Do NOT include any text before or after the JSON. "
        f"Do NOT wrap the JSON in markdown code blocks."
    )
