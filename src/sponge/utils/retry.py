"""Async retry with exponential backoff for LLM calls."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

logger = logging.getLogger("sponge.utils.retry")

T = TypeVar("T")

_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
)


async def retry(  # noqa: UP047
    fn: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,  # noqa: ANN401
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    retryable: tuple[type[BaseException], ...] = _RETRYABLE_EXCEPTIONS,
    **kwargs: Any,  # noqa: ANN401
) -> T:
    """Call an async function with exponential backoff retry.

    Args:
        fn: Async function to call.
        *args: Positional arguments for fn.
        max_attempts: Maximum number of attempts (including the first).
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay between retries.
        backoff: Multiplier for successive delays.
        retryable: Exception types that trigger a retry.
        **kwargs: Keyword arguments for fn.

    Returns:
        The return value of fn.

    Raises:
        The last exception if all attempts fail.
    """
    last_exc: BaseException | None = None
    delay = base_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except retryable as e:
            last_exc = e
            if attempt == max_attempts:
                raise
            logger.warning(
                "Retry %d/%d after %.1fs: %s",
                attempt,
                max_attempts,
                delay,
                e,
            )
            await asyncio.sleep(delay)
            delay = min(delay * backoff, max_delay)

    # Should never reach here, but satisfy type checker.
    assert last_exc is not None
    raise last_exc
