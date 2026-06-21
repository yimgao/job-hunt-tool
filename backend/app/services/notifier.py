"""Telegram 通知服务 — 高匹配职位即时推送。

配置 (.env):
    TELEGRAM_BOT_TOKEN=xxx
    TELEGRAM_CHAT_ID=xxx

未配置时静默降级（返回 False，不抛异常）。
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    """通过 Telegram Bot API 发送通知。"""

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    @property
    def _configured(self) -> bool:
        return bool(self.token and self.chat_id)

    async def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """发送原始消息。返回是否成功。"""
        if not self._configured:
            logger.debug("Telegram not configured — skipping notification")
            return False
        url = _TELEGRAM_API.format(token=self.token)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    json={"chat_id": self.chat_id, "text": message, "parse_mode": parse_mode},
                )
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.warning("Telegram send failed: %s", exc)
            return False

    async def notify_match(
        self,
        job_title: str,
        company: str,
        score: float,
        priority: str = "medium",
        apply_url: str | None = None,
    ) -> bool:
        """新高匹配职位通知。"""
        emoji = "🔥" if priority == "high" else "✨"
        lines = [
            f"{emoji} <b>新高匹配职位</b>",
            f"<b>{job_title}</b> @ {company}",
            f"匹配度: <code>{score:.0%}</code>  优先级: {priority.upper()}",
        ]
        if apply_url:
            lines.append(f'<a href="{apply_url}">前往投递 ↗</a>')
        return await self.send("\n".join(lines))

    async def notify_applied(self, job_title: str, company: str) -> bool:
        """投递完成通知。"""
        msg = f"✅ <b>投递完成</b>\n{job_title} @ {company}"
        return await self.send(msg)

    async def notify_pipeline_error(self, error: str) -> bool:
        """流水线异常通知。"""
        msg = f"⚠️ <b>Pipeline 异常</b>\n<code>{error[:200]}</code>"
        return await self.send(msg)

    async def notify_daily_summary(self, stats: dict[str, Any]) -> bool:
        """每日摘要推送。"""
        lines = [
            "📊 <b>JobHunt-Flow 日报</b>",
            f"新职位: {stats.get('new_jobs', 0)}",
            f"高匹配 (≥60%): {stats.get('high_match', 0)}",
            f"已投递: {stats.get('applied', 0)}",
            f"今日成本: ${stats.get('cost', 0):.4f}",
        ]
        return await self.send("\n".join(lines))


notifier = TelegramNotifier()
