"""Token counting using tiktoken."""

# Approximate tokens-per-character for models without tiktoken encodings.
_FALLBACK_CHARS_PER_TOKEN = 4


# Known tiktoken encoding overrides per model family.
_MODEL_ENCODINGS: dict[str, str] = {
    "claude": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-5": "o200k_base",
    "deepseek": "cl100k_base",
}


def _guess_encoding(model: str) -> str | None:
    """Try to find a matching tiktoken encoding for a model."""
    model_lower = model.lower()
    for prefix, encoding in _MODEL_ENCODINGS.items():
        if model_lower.startswith(prefix):
            return encoding
    return None


def count_tokens(text: str, model: str = "claude-sonnet-4") -> int:
    """Count tokens in text for a given model.

    Uses tiktoken when an encoding is known, falls back to character-based
    approximation otherwise.

    Args:
        text: The text to count tokens for.
        model: Model identifier to select the right tokenizer.

    Returns:
        Estimated token count.
    """
    encoding_name = _guess_encoding(model)

    if encoding_name is not None:
        try:
            import tiktoken

            enc = tiktoken.get_encoding(encoding_name)
            return len(enc.encode(text))
        except (ImportError, ValueError):
            pass

    # Fallback: rough character-based estimate.
    return max(1, len(text) // _FALLBACK_CHARS_PER_TOKEN)


def count_tokens_batch(texts: list[str], model: str = "claude-sonnet-4") -> int:
    """Count tokens across multiple text strings."""
    return sum(count_tokens(t, model) for t in texts)
