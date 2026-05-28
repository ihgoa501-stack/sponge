"""Tests for the reflection module — the bronze mirror."""

import json
import textwrap

import pytest

from sponge.core.reflection import (
    Lesson,
    ReflectionModule,
    ReflectionResult,
    _build_reflection_messages,
    _parse_reflection_json,
    extract_lesson,
)
from sponge.llm.base import Message


# ---------------------------------------------------------------------------
# ReflectionResult
# ---------------------------------------------------------------------------


class TestReflectionResult:
    def test_defaults(self):
        r = ReflectionResult(root_cause="test")
        assert r.root_cause == "test"
        assert r.contributing_factors == []
        assert r.novel_pattern is True
        assert r.preventive_rule == ""
        assert r.severity == "medium"
        assert r.confidence == 0.0

    def test_full_construction(self):
        r = ReflectionResult(
            root_cause="Edited wrong file",
            contributing_factors=["Did not read file first", "Assumed structure"],
            novel_pattern=False,
            preventive_rule="Always read before edit",
            severity="high",
            confidence=0.95,
        )
        assert r.root_cause == "Edited wrong file"
        assert len(r.contributing_factors) == 2
        assert r.novel_pattern is False
        assert r.preventive_rule == "Always read before edit"
        assert r.severity == "high"
        assert r.confidence == 0.95


# ---------------------------------------------------------------------------
# Lesson
# ---------------------------------------------------------------------------


class TestLesson:
    def test_to_context_line(self):
        lesson = Lesson(
            id="ref_001",
            condition="file_edit",
            action="Edited src/auth.py",
            observed_outcome="Broke tests",
            lesson="Always run tests after editing src/auth.py",
        )
        assert lesson.id in lesson.to_context_line()
        assert "Always run tests" in lesson.to_context_line()

    def test_no_id(self):
        lesson = Lesson(
            condition="general",
            action="did something",
            observed_outcome="it broke",
            lesson="don't do that",
        )
        line = lesson.to_context_line()
        assert "[ ]" in line or "[]" in line  # empty id


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


class TestParseReflectionJson:
    def test_clean_json(self):
        data = {
            "root_cause": "Agent did not read file before editing.",
            "contributing_factors": ["Missing context", "Assumed structure"],
            "novel_pattern": True,
            "preventive_rule": "Always read_file before edit_file in src/auth/.",
            "severity": "medium",
            "confidence": 0.85,
        }
        result = _parse_reflection_json(json.dumps(data))
        assert result is not None
        assert result.root_cause == data["root_cause"]
        assert result.contributing_factors == data["contributing_factors"]
        assert result.novel_pattern is True
        assert result.preventive_rule == data["preventive_rule"]
        assert result.severity == "medium"
        assert result.confidence == 0.85

    def test_markdown_fence(self):
        data = {"root_cause": "x", "confidence": 0.5}
        raw = "```json\n" + json.dumps(data) + "\n```"
        result = _parse_reflection_json(raw)
        assert result is not None
        assert result.root_cause == "x"

    def test_json_buried_in_text(self):
        data = {"root_cause": "buried", "confidence": 0.6}
        raw = "Here's my analysis:\n\n" + json.dumps(data) + "\n\nHope that helps!"
        result = _parse_reflection_json(raw)
        assert result is not None
        assert result.root_cause == "buried"

    def test_invalid_json_returns_none(self):
        result = _parse_reflection_json("not json at all")
        assert result is None

    def test_empty_string_returns_none(self):
        result = _parse_reflection_json("")
        assert result is None

    def test_missing_fields_get_defaults(self):
        data = {"root_cause": "only this"}
        result = _parse_reflection_json(json.dumps(data))
        assert result is not None
        assert result.root_cause == "only this"
        assert result.contributing_factors == []
        assert result.preventive_rule == ""


# ---------------------------------------------------------------------------
# Message building
# ---------------------------------------------------------------------------


class TestBuildReflectionMessages:
    def test_basic(self):
        msgs = _build_reflection_messages(
            task_prompt="Fix the login bug",
            messages=[Message(role="user", content="Fix the login bug")],
            response="I tried but failed.",
            failure_reason="User said the output was wrong.",
        )
        assert len(msgs) == 2
        assert msgs[0].role == "system"
        assert "diagnostic evaluator" in msgs[0].content
        assert msgs[1].role == "user"
        assert "Fix the login bug" in msgs[1].content
        assert "User said the output was wrong" in msgs[1].content

    def test_truncates_long_response(self):
        long_response = "x" * 3000
        msgs = _build_reflection_messages(
            task_prompt="test",
            messages=[],
            response=long_response,
            failure_reason="failed",
        )
        user_content = msgs[1].content
        # Response should be truncated to ~2000 chars
        assert "xxx" in user_content
        assert len(user_content) < 4000  # generous upper bound

    def test_truncates_many_messages(self):
        messages = [
            Message(role="user", content=f"Message {i}: " + "x" * 200)
            for i in range(50)
        ]
        msgs = _build_reflection_messages(
            task_prompt="test",
            messages=messages,
            response="failed",
            failure_reason="error",
        )
        user_content = msgs[1].content
        # Should have truncated some messages
        assert "remaining messages truncated" in user_content.lower()


# ---------------------------------------------------------------------------
# extract_lesson
# ---------------------------------------------------------------------------


class TestExtractLesson:
    def test_basic(self):
        reflection = ReflectionResult(
            root_cause="Agent edited test_auth.py without reading it first.",
            preventive_rule="Always read_file before edit_file in test files.",
            severity="high",
            confidence=0.9,
        )
        lesson = extract_lesson(
            reflection,
            task_prompt="Fix failing tests in test_auth.py",
            condition_tags=["file_edit", "test_breakage"],
        )
        assert lesson.condition == "file_edit | test_breakage | Fix failing tests in test_auth.py"
        assert lesson.lesson == reflection.preventive_rule
        assert lesson.severity == "high"
        assert lesson.observed_outcome == reflection.root_cause

    def test_no_tags(self):
        reflection = ReflectionResult(
            root_cause="Something went wrong.",
            preventive_rule="Be more careful.",
        )
        lesson = extract_lesson(
            reflection,
            task_prompt="Do the thing",
        )
        assert "Do the thing" in lesson.condition


# ---------------------------------------------------------------------------
# ReflectionModule (integration, uses MockProvider)
# ---------------------------------------------------------------------------


class MockReflectionProvider:
    """Mock provider that returns a specific JSON reflection."""

    def __init__(self, json_data: dict | None = None, fail: bool = False):
        self.json_data = json_data or {
            "root_cause": "Test root cause.",
            "contributing_factors": ["Factor A", "Factor B"],
            "novel_pattern": True,
            "preventive_rule": "Test preventive rule.",
            "severity": "medium",
            "confidence": 0.85,
        }
        self._fail = fail
        self.calls: list[list[Message]] = []

    async def stream(self, messages, model=None, **kwargs):
        from sponge.llm.base import ContentDelta, UsageEvent
        from sponge.cost.models import Usage

        self.calls.append(messages)
        if self._fail:
            raise RuntimeError("Simulated provider failure")
        text = json.dumps(self.json_data)
        yield ContentDelta(text=text)
        yield UsageEvent(usage=Usage(tokens_in=100, tokens_out=50))


@pytest.mark.asyncio
async def test_reflect_success():
    provider = MockReflectionProvider()
    module = ReflectionModule(provider)

    result = await module.reflect(
        task_prompt="Fix the login bug",
        messages=[Message(role="user", content="Fix the login bug")],
        response="I edited login.py but the tests still fail.",
        failure_reason="User reported: tests still fail after edit.",
    )

    assert result is not None
    assert result.root_cause == "Test root cause."
    assert result.preventive_rule == "Test preventive rule."
    assert result.confidence == 0.85
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_reflect_provider_failure():
    provider = MockReflectionProvider(fail=True)
    module = ReflectionModule(provider)

    result = await module.reflect(
        task_prompt="test",
        messages=[],
        response="failed",
        failure_reason="error",
    )
    assert result is None


@pytest.mark.asyncio
async def test_reflect_low_confidence_discarded():
    provider = MockReflectionProvider(
        json_data={
            "root_cause": "uncertain",
            "contributing_factors": [],
            "novel_pattern": True,
            "preventive_rule": "maybe something",
            "severity": "low",
            "confidence": 0.3,
        }
    )
    module = ReflectionModule(provider)

    result = await module.reflect(
        task_prompt="test",
        messages=[],
        response="failed",
        failure_reason="error",
    )
    assert result is None  # confidence < 0.5


@pytest.mark.asyncio
async def test_reflect_unparseable_response():
    """Provider returns non-JSON text."""
    from sponge.llm.base import ContentDelta, UsageEvent
    from sponge.cost.models import Usage

    class BadProvider:
        async def stream(self, messages, model=None, **kwargs):
            yield ContentDelta(text="I don't know what happened, sorry.")
            yield UsageEvent(usage=Usage(tokens_in=100, tokens_out=20))

    module = ReflectionModule(BadProvider())
    result = await module.reflect(
        task_prompt="test",
        messages=[],
        response="failed",
        failure_reason="error",
    )
    assert result is None
