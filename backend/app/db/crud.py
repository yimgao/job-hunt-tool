"""DB CRUD helpers — called from agent nodes (no FastAPI DI context)."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.application import Application
from app.db.models.job import Job
from app.db.models.user import User
from app.db.session import async_session

logger = logging.getLogger(__name__)

_DEFAULT_USER_ID: uuid.UUID | None = None
_DEFAULT_USER_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_or_create_default_user() -> uuid.UUID:
    """Return the default user UUID, creating the row if it doesn't exist."""
    global _DEFAULT_USER_ID
    if _DEFAULT_USER_ID:
        return _DEFAULT_USER_ID

    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.id == _DEFAULT_USER_UUID)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                id=_DEFAULT_USER_UUID,
                name="Default User",
                email="default@jobhunt.local",
            )
            db.add(user)
            await db.commit()

    _DEFAULT_USER_ID = _DEFAULT_USER_UUID
    return _DEFAULT_USER_ID


async def bulk_upsert_jobs(job_dicts: list[dict]) -> list[uuid.UUID]:
    """Insert new jobs; skip existing ones (matched by content_hash or source_id).

    Returns list of job UUIDs (both new and pre-existing).
    """
    if not job_dicts:
        return []

    saved_ids: list[uuid.UUID] = []

    async with async_session() as db:
        for j in job_dicts:
            existing_id = await _find_existing_job(db, j)
            if existing_id:
                saved_ids.append(existing_id)
                continue

            job_id = uuid.uuid4()
            job = Job(
                id=job_id,
                source=j.get("source", "unknown"),
                source_id=j.get("source_id"),
                title=(j.get("title") or "")[:255],
                company=(j.get("company") or "")[:255],
                location=j.get("location"),
                salary_min=j.get("salary_min"),
                salary_max=j.get("salary_max"),
                jd_text=j.get("jd_text", ""),
                skills=j.get("skills"),
                content_hash=j.get("content_hash"),
                url=j.get("url"),
                posted_at=j.get("posted_at"),
            )
            db.add(job)
            saved_ids.append(job_id)

        await db.commit()

    logger.info("bulk_upsert_jobs: %d/%d jobs persisted", len(saved_ids), len(job_dicts))
    return saved_ids


async def _find_existing_job(db: AsyncSession, j: dict) -> uuid.UUID | None:
    content_hash = j.get("content_hash")
    if content_hash:
        result = await db.execute(
            select(Job.id).where(Job.content_hash == content_hash)
        )
        row = result.scalar_one_or_none()
        if row:
            return row

    source_id = j.get("source_id")
    if source_id:
        result = await db.execute(
            select(Job.id).where(Job.source_id == source_id)
        )
        row = result.scalar_one_or_none()
        if row:
            return row

    return None


async def upsert_application(
    job_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
    match_score: float | None = None,
    match_report: dict | None = None,
    cover_letter: str | None = None,
) -> uuid.UUID:
    """Create or update an Application record; return its UUID."""
    async with async_session() as db:
        result = await db.execute(
            select(Application)
            .where(Application.job_id == job_id)
            .where(Application.user_id == user_id)
        )
        app = result.scalar_one_or_none()

        if app:
            app.status = status
            if match_score is not None:
                app.match_score = match_score
            if match_report is not None:
                app.match_report = match_report
            if cover_letter is not None:
                app.tailored_cover_letter = cover_letter
            app_id = app.id
        else:
            app_id = uuid.uuid4()
            app = Application(
                id=app_id,
                job_id=job_id,
                user_id=user_id,
                status=status,
                match_score=match_score,
                match_report=match_report,
                tailored_cover_letter=cover_letter,
            )
            db.add(app)

        await db.commit()

    logger.info("upsert_application: %s (job=%s status=%s)", app_id, job_id, status)
    return app_id
