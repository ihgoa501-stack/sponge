"""Tests for retry utility."""

import pytest

from sponge.utils.retry import retry


async def test_retry_succeeds_first_attempt() -> None:
    call_count = 0

    async def work() -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await retry(work)
    assert result == "ok"
    assert call_count == 1


async def test_retry_eventually_succeeds() -> None:
    call_count = 0

    async def work() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("fail")
        return "ok"

    result = await retry(work, base_delay=0.01)
    assert result == "ok"
    assert call_count == 3


async def test_retry_raises_after_max_attempts() -> None:
    async def work() -> str:
        raise ConnectionError("always fail")

    with pytest.raises(ConnectionError):
        await retry(work, max_attempts=2, base_delay=0.01)
