"""VectorStore — pgvector 嵌入存储与余弦相似度检索。

Phase 4 完整实现:
  - embed()       : OpenAI text-embedding-3-small
  - add_chunk()   : INSERT INTO resume_chunks WITH embedding
  - search()      : pgvector cosine distance 召回
  - chunk_resume(): 段落切块（无 LLM 依赖）

降级: 无 API key 或无 DB session → 返回 mock/空结果，不抛异常。
"""
from __future__ import annotations

import logging
import os
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.resume_chunk import EMBEDDING_DIM, ResumeChunk

logger = logging.getLogger(__name__)


class VectorStore:
    """简历 chunk 的向量存储和检索。"""

    def __init__(self, db_session: AsyncSession | None = None):
        self.db = db_session
        api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")

    # ── Embedding ─────────────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        """文本 → embedding vector。无 API key 时返回零向量。"""
        if not self.client:
            return [0.0] * EMBEDDING_DIM
        try:
            resp = await self.client.embeddings.create(
                model=self.embed_model,
                input=text[:8000],
            )
            return resp.data[0].embedding
        except Exception as exc:
            logger.warning("embed failed: %s — returning zero vector", exc)
            return [0.0] * EMBEDDING_DIM

    # ── Write ─────────────────────────────────────────────────────────────────

    async def add_chunk(
        self, user_id: str, chunk_type: str, content: str
    ) -> dict[str, Any]:
        """嵌入并存储一个简历 chunk。"""
        embedding = await self.embed(content)

        if not self.db:
            return {"chunk_id": "mock", "embedding_dim": len(embedding)}

        import uuid as uuid_mod
        chunk = ResumeChunk(
            user_id=uuid_mod.UUID(user_id),
            chunk_type=chunk_type,
            content=content,
            embedding=embedding,
        )
        self.db.add(chunk)
        await self.db.commit()
        await self.db.refresh(chunk)
        return {"chunk_id": str(chunk.id), "embedding_dim": len(embedding)}

    # ── Read ──────────────────────────────────────────────────────────────────

    async def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.6,
    ) -> list[dict[str, Any]]:
        """余弦相似度召回最相关的简历 chunks。

        threshold: 相似度下限（1 - cosine_distance）。
        """
        if not self.db:
            return []

        query_vec = await self.embed(query)
        if all(v == 0.0 for v in query_vec):
            return []

        import uuid as uuid_mod
        uid = uuid_mod.UUID(user_id)

        # cosine_distance ∈ [0, 2], lower = more similar; threshold maps to distance < 1-t
        max_dist = 1.0 - threshold
        stmt = (
            select(
                ResumeChunk.id,
                ResumeChunk.chunk_type,
                ResumeChunk.content,
                ResumeChunk.embedding.cosine_distance(query_vec).label("distance"),
            )
            .where(ResumeChunk.user_id == uid)
            .where(ResumeChunk.embedding.cosine_distance(query_vec) < max_dist)
            .order_by("distance")
            .limit(top_k)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "chunk_id": str(row.id),
                "chunk_type": row.chunk_type,
                "content": row.content,
                "similarity": round(1.0 - row.distance, 4),
            }
            for row in rows
        ]

    # ── Chunking ──────────────────────────────────────────────────────────────

    async def chunk_resume(self, resume_text: str) -> list[str]:
        """将简历全文按双换行切块，过滤太短片段，最多 20 块。"""
        paragraphs = [p.strip() for p in resume_text.split("\n\n") if p.strip()]
        return [p for p in paragraphs if len(p) > 50][:20]
