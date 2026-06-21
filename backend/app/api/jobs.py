"""GET/POST /api/jobs — 职位 CRUD。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import Job
from app.db.session import get_db
from app.schemas.job import JobCreate, JobResponse
from app.services.dedup import compute_content_hash

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    """列出职位，支持按 source 过滤。"""
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    if source:
        stmt = stmt.where(Job.source == source)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)) -> JobResponse:
    """获取单条职位详情。"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    payload: JobCreate, db: AsyncSession = Depends(get_db)
) -> JobResponse:
    """创建职位（供内部测试和 Scraper Agent 使用）。"""
    content_hash = compute_content_hash(payload.jd_text)

    existing = await db.execute(
        select(Job).where(Job.content_hash == content_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Duplicate job (same content hash)")

    job = Job(
        source=payload.source,
        source_id=payload.source_id,
        title=payload.title,
        company=payload.company,
        location=payload.location,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        jd_text=payload.jd_text,
        skills=payload.skills,
        content_hash=content_hash,
        url=payload.url,
        posted_at=payload.posted_at,
    )
    db.add(job)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate job (content hash or source_id conflict)")
    await db.refresh(job)
    return JobResponse.model_validate(job)
