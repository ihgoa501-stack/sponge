"""Tests for token counting."""

from unittest import mock

import pytest

from sponge.llm.token_counter import (
    _FALLBACK_CHARS_PER_TOKEN,
    _guess_encoding,
    count_tokens,
    count_tokens_batch,
)


def test_guess_encoding_claude() -> None:
    """Claude models map to cl100k_base."""
    assert _guess_encoding("claude-sonnet-4") == "cl100k_base"
    assert _guess_encoding("claude-haiku-3-5") == "cl100k_base"
    assert _guess_encoding("claude-opus-4-7") == "cl100k_base"


def test_guess_encoding_gpt4o() -> None:
    """GPT-4o models map to o200k_base (longest-prefix-first ordering)."""
    assert _guess_encoding("gpt-4o") == "o200k_base"
    assert _guess_encoding("gpt-4o-mini") == "o200k_base"
    assert _guess_encoding("gpt-5") == "o200k_base"


def test_guess_encoding_gpt4() -> None:
    """GPT-4 maps to cl100k_base."""
    assert _guess_encoding("gpt-4") == "cl100k_base"


def test_guess_encoding_deepseek() -> None:
    """DeepSeek models map to cl100k_base."""
    assert _guess_encoding("deepseek-v4-flash") == "cl100k_base"
    assert _guess_encoding("deepseek-r1") == "cl100k_base"


def test_guess_encoding_unknown() -> None:
    """Unknown model returns None."""
    assert _guess_encoding("totally-unknown-model") is None


def test_count_tokens_with_tiktoken() -> None:
    """Known model uses tiktoken for accurate count."""
    # Claude models use cl100k_base.
    count = count_tokens("Hello world", "claude-sonnet-4")
    # "Hello world" is 2 tokens in cl100k_base.
    assert count == 2


def test_count_tokens_fallback_unknown_model() -> None:
    """Unknown model falls back to character-based approximation."""
    count = count_tokens("Hello world!", "unknown-model")
    # len("Hello world!") = 12, 12 // 4 = 3, but max(1, 3) = 3
    expected = max(1, len("Hello world!") // _FALLBACK_CHARS_PER_TOKEN)
    assert count == expected


def test_count_tokens_empty_string() -> None:
    """Empty string returns at least 1 token (max(1, 0))."""
    count = count_tokens("", "unknown-model")
    assert count == 1


def test_count_tokens_batch() -> None:
    """count_tokens_batch sums across multiple strings."""
    total = count_tokens_batch(["Hello", "world"], "claude-sonnet-4")
    # "Hello" = 1 token, "world" = 1 token in cl100k_base.
    assert total == 2


def test_count_tokens_batch_empty() -> None:
    """Empty batch returns 0."""
    assert count_tokens_batch([], "claude-sonnet-4") == 0


def test_count_tokens_tiktoken_not_installed() -> None:
    """When tiktoken import fails, falls back to char-based estimate."""
    with mock.patch.dict("sys.modules", {"tiktoken": None}):
        # Force tiktoken import to fail.
        with mock.patch("builtins.__import__", side_effect=ImportError):
            count = count_tokens("Hello world!", "claude-sonnet-4")
            expected = max(1, len("Hello world!") // _FALLBACK_CHARS_PER_TOKEN)
            assert count == expected
