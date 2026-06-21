"""指数退避重试装饰器。"""
from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Type

logger = logging.getLogger(__name__)


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """异步函数重试装饰器，指数退避。

    Args:
        max_retries: 最大重试次数（含首次调用）。
        base_delay: 初始等待秒数，每次 ×2。
        exceptions: 触发重试的异常类型。
    """
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "%s attempt %d/%d failed: %s — retrying in %.1fs",
                            fn.__name__, attempt + 1, max_retries, exc, delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            fn.__name__, max_retries, exc,
                        )
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator
