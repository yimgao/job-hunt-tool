"""Pydantic schema for Application API."""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    match_score: float | None = None
    match_report: dict | None = None
    tailored_resume_url: str | None = None
    tailored_cover_letter: str | None = None
    error_log: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApplicationUpdate(BaseModel):
    status: str | None = None
    match_score: float | None = None
    match_report: dict | None = None
    tailored_resume_url: str | None = None
    tailored_cover_letter: str | None = None
    error_log: str | None = None
