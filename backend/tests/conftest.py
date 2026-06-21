"""共享 fixtures。"""
from __future__ import annotations
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

LONG_RESUME = "A" * 200
LONG_JD = "B" * 200


@pytest.fixture
async def client():
    """FastAPI 测试客户端 — patch init_db 避免连接真实数据库。"""
    with patch("app.main.init_db", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
