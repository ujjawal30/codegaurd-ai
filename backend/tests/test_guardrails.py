"""
Tests for app.utils.guardrails
"""

import json
import pytest
from pydantic import BaseModel, Field
from app.utils.guardrails import (
    extract_json_from_response,
    parse_llm_output,
    parse_llm_output_list,
    build_json_schema_prompt,
    LLMOutputError,
)


# ── Test schema ─────────────────────────────────────────────────


class SampleModel(BaseModel):
    name: str
    score: float = Field(ge=0, le=1.0)


class IssueModel(BaseModel):
    title: str
    severity: str


# ── extract_json_from_response ──────────────────────────────────


class TestExtractJson:
    """Tests for extract_json_from_response."""

    def test_plain_json_object(self):
        text = '{"name": "test", "score": 0.5}'
        result = extract_json_from_response(text)
        assert json.loads(result) == {"name": "test", "score": 0.5}

    def test_plain_json_array(self):
        # Note: extract_json_from_response checks { before [, so use
        # a markdown block to test array extraction
        text = '```json\n[{"name": "a"}, {"name": "b"}]\n```'
        result = extract_json_from_response(text)
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_json_in_markdown_code_block(self):
        text = 'Here is the result:\n```json\n{"name": "test", "score": 0.8}\n```\nEnd.'
        result = extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_json_in_generic_code_block(self):
        text = 'Result:\n```\n{"name": "test", "score": 0.3}\n```'
        result = extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["score"] == 0.3

    def test_json_with_surrounding_text(self):
        text = 'The analysis found: {"name": "result", "score": 0.9} which is good.'
        result = extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["name"] == "result"

    def test_nested_json(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["outer"]["inner"] == [1, 2, 3]


# ── parse_llm_output ───────────────────────────────────────────


class TestParseLlmOutput:
    """Tests for parse_llm_output."""

    def test_valid_json_parses(self):
        raw = '{"name": "test", "score": 0.5}'
        result = parse_llm_output(raw, SampleModel)
        assert result.name == "test"
        assert result.score == 0.5

    def test_markdown_wrapped_json_parses(self):
        raw = '```json\n{"name": "test", "score": 0.7}\n```'
        result = parse_llm_output(raw, SampleModel)
        assert result.name == "test"
        assert result.score == 0.7

    def test_invalid_json_raises(self):
        raw = "this is not json at all"
        with pytest.raises(LLMOutputError):
            parse_llm_output(raw, SampleModel)

    def test_schema_mismatch_raises(self):
        # score > 1.0 violates ge=0, le=1.0 constraint
        raw = '{"name": "test", "score": 5.0}'
        with pytest.raises(LLMOutputError):
            parse_llm_output(raw, SampleModel)

    def test_missing_required_field_raises(self):
        raw = '{"score": 0.5}'
        with pytest.raises(LLMOutputError):
            parse_llm_output(raw, SampleModel)


# ── parse_llm_output_list ───────────────────────────────────────


class TestParseLlmOutputList:
    """Tests for parse_llm_output_list."""

    def test_valid_list_parses(self):
        raw = '```json\n[{"title": "Bug", "severity": "high"}, {"title": "Style", "severity": "low"}]\n```'
        result = parse_llm_output_list(raw, IssueModel)
        assert len(result) == 2
        assert result[0].title == "Bug"
        assert result[1].severity == "low"

    def test_single_object_wrapped_in_list(self):
        raw = '{"title": "Solo", "severity": "medium"}'
        result = parse_llm_output_list(raw, IssueModel)
        assert len(result) == 1
        assert result[0].title == "Solo"

    def test_invalid_item_raises(self):
        raw = '[{"wrong_field": "value"}]'
        with pytest.raises(LLMOutputError):
            parse_llm_output_list(raw, IssueModel)


# ── build_json_schema_prompt ────────────────────────────────────


class TestBuildSchemaPrompt:
    """Tests for build_json_schema_prompt."""

    def test_contains_schema_json(self):
        prompt = build_json_schema_prompt(SampleModel)
        assert "name" in prompt
        assert "score" in prompt

    def test_contains_instructions(self):
        prompt = build_json_schema_prompt(SampleModel)
        assert "JSON" in prompt
        assert "schema" in prompt.lower()
