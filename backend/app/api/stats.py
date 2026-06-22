"""GET /api/stats/* — 系统统计数据。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.job import Job
from app.db.models.application import Application

router = APIRouter(prefix="/api/stats", tags=["stats"])

COST_PER_JOB = 0.002  # 每个职位的估算成本 (初筛 Gemini≈0, 深度 GPT-4o-mini≈$0.001, embedding≈$0.001)


class DailyStat(BaseModel):
    date: str
    jobs: int
    applications: int
    cost: float


class StatsResponse(BaseModel):
    totals: dict[str, int]
    daily: list[DailyStat]
    cost_total: float


@router.get("/daily", response_model=StatsResponse)
async def daily_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """返回最近 N 天的统计数据（职位数、投递数、估算成本）。"""
    now = datetime.now(timezone.utc)

    total_jobs = await db.scalar(select(func.count()).select_from(Job)) or 0
    total_apps = await db.scalar(select(func.count()).select_from(Application)) or 0

    daily: list[DailyStat] = []
    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        jobs_today = await db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.created_at >= day_start)
            .where(Job.created_at < day_end)
        ) or 0

        apps_today = await db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.created_at >= day_start)
            .where(Application.created_at < day_end)
        ) or 0

        daily.append(
            DailyStat(
                date=day_start.strftime("%m/%d"),
                jobs=jobs_today,
                applications=apps_today,
                cost=round(jobs_today * COST_PER_JOB, 4),
            )
        )

    return StatsResponse(
        totals={"jobs": total_jobs, "applications": total_apps},
        daily=daily,
        cost_total=round(total_jobs * COST_PER_JOB, 4),
    )
