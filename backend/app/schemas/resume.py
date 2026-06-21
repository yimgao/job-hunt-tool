"""Pydantic schemas for Resume Chunk API."""
from __future__ import annotations
from pydantic import BaseModel, Field


class ChunkCreate(BaseModel):
    user_id: str = Field(description="用户 UUID")
    chunk_type: str = Field(
        description="chunk 类型: experience / education / project / skill",
        pattern="^(experience|education|project|skill|other)$",
    )
    content: str = Field(min_length=20, description="chunk 正文（至少 20 字符）")


class ChunkResponse(BaseModel):
    chunk_id: str
    embedding_dim: int
    message: str = "chunk added"


class ResumeIngestRequest(BaseModel):
    """一次性上传完整简历文本，自动切块并向量化。"""
    user_id: str
    resume_text: str = Field(min_length=100)
