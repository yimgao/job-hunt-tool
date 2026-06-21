"""Pydantic schema for Job API."""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel


class JobCreate(BaseModel):
    source: str
    source_id: str | None = None
    title: str
    company: str
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    jd_text: str
    skills: dict | None = None
    url: str | None = None
    posted_at: datetime | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    source: str
    title: str
    company: str
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    skills: dict | None = None
    url: str | None = None
    posted_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
