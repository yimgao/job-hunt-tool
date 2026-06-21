"""Tests for exponential-backoff retry decorator."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.utils.retry import with_retry


@pytest.mark.asyncio
async def test_success_on_first_attempt():
    calls = 0

    @with_retry(max_retries=3)
    async def fn():
        nonlocal calls
        calls += 1
        return "ok"

    result = await fn()
    assert result == "ok"
    assert calls == 1


@pytest.mark.asyncio
async def test_retries_on_transient_error():
    calls = 0

    @with_retry(max_retries=3, base_delay=0.0)
    async def fn():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("transient")
        return "recovered"

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await fn()

    assert result == "recovered"
    assert calls == 3


@pytest.mark.asyncio
async def test_raises_after_max_retries():
    calls = 0

    @with_retry(max_retries=2, base_delay=0.0)
    async def fn():
        nonlocal calls
        calls += 1
        raise RuntimeError("always fails")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="always fails"):
            await fn()

    assert calls == 2


@pytest.mark.asyncio
async def test_only_retries_specified_exceptions():
    @with_retry(max_retries=3, base_delay=0.0, exceptions=(ValueError,))
    async def fn():
        raise TypeError("not in filter")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(TypeError):
            await fn()


@pytest.mark.asyncio
async def test_exponential_backoff_delays():
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)

    @with_retry(max_retries=3, base_delay=1.0)
    async def fn():
        raise RuntimeError("fail")

    with patch("asyncio.sleep", side_effect=fake_sleep):
        with pytest.raises(RuntimeError):
            await fn()

    # Should sleep base*2^0=1.0, base*2^1=2.0
    assert sleep_calls == [1.0, 2.0]
