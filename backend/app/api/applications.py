"""GET/PATCH /api/applications — 投递记录 CRUD。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.application import Application
from app.db.session import get_db
from app.schemas.application import ApplicationResponse, ApplicationUpdate

router = APIRouter(prefix="/api", tags=["applications"])

VALID_STATUSES = {"scraped", "matched", "tailored", "applied", "rejected", "archived"}


@router.get("/applications", response_model=list[ApplicationResponse])
async def list_applications(
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationResponse]:
    """列出投递记录，支持 status 过滤。"""
    stmt = (
        select(Application)
        .order_by(Application.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
            )
        stmt = stmt.where(Application.status == status)
    result = await db.execute(stmt)
    apps = result.scalars().all()
    return [ApplicationResponse.model_validate(a) for a in apps]


@router.get("/applications/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: str, db: AsyncSession = Depends(get_db)
) -> ApplicationResponse:
    """获取单条投递详情。"""
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationResponse.model_validate(app)


@router.patch("/applications/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: str,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """更新投递状态或报告字段。"""
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if payload.status and payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, field, value)

    await db.commit()
    await db.refresh(app)
    return ApplicationResponse.model_validate(app)
