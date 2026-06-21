"""Application ORM model — 投递状态机."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="scraped",
    )
    match_score: Mapped[float | None] = mapped_column(Float)
    match_report: Mapped[dict | None] = mapped_column(JSONB)
    tailored_resume_url: Mapped[str | None] = mapped_column(Text)
    tailored_cover_letter: Mapped[str | None] = mapped_column(Text)
    extension_task_id: Mapped[str | None] = mapped_column(String(255))
    error_log: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job = relationship("Job", back_populates="applications")
    user = relationship("User", back_populates="applications")
