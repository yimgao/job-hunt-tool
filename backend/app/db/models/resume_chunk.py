"""ResumeChunk ORM model — 简历分块向量库 (pgvector)。

启动前需在 PostgreSQL 中启用扩展（init_db 会自动执行）:
    CREATE EXTENSION IF NOT EXISTS vector;
"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base

EMBEDDING_DIM = 1536  # text-embedding-3-small default; bge-small → 512


class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    chunk_type: Mapped[str] = mapped_column(String(50))  # experience / education / project
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="resume_chunks")

    __table_args__ = (
        Index("idx_resume_chunks_user", "user_id"),
    )
