"""Tests for TelegramNotifier — verifies message construction without real HTTP calls."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture()
def notifier():
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "12345",
    }):
        from importlib import reload
        import app.services.notifier as mod
        reload(mod)
        yield mod.TelegramNotifier()


@pytest.mark.asyncio
async def test_notify_match_sends_message(notifier):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        await notifier.notify_match(
            job_title="Backend Engineer",
            company="Acme Corp",
            score=0.85,
            priority="high",
            apply_url="https://example.com/apply",
        )

        assert mock_client.post.called
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"] if call_kwargs[1] else call_kwargs[0][1]
        assert "Backend Engineer" in payload["text"]
        assert "Acme Corp" in payload["text"]


@pytest.mark.asyncio
async def test_notify_applied(notifier):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        await notifier.notify_applied("SWE Intern", "BigTech")
        assert mock_client.post.called


@pytest.mark.asyncio
async def test_notify_daily_summary(notifier):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        stats = {"new_jobs": 12, "high_match": 3, "applied": 1, "cost": 0.05}
        await notifier.notify_daily_summary(stats)
        assert mock_client.post.called


@pytest.mark.asyncio
async def test_notify_silenced_when_no_credentials():
    """Notifier should not crash when token/chat_id missing — just log and return."""
    with patch.dict("os.environ", {}, clear=True):
        from importlib import reload
        import app.services.notifier as mod
        reload(mod)
        n = mod.TelegramNotifier()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        # Should not raise, should not call post
        await n.notify_match("Job", "Co", 0.9, "high", "https://x.com")
        assert not mock_client.post.called
