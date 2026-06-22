"""POST /api/resume/* — 简历向量化入库。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.db.session import get_db
from app.schemas.resume import ChunkCreate, ChunkResponse, ResumeIngestRequest
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/chunks", response_model=ChunkResponse, status_code=201, dependencies=[Depends(verify_api_key)])
async def add_chunk(
    req: ChunkCreate, db: AsyncSession = Depends(get_db)
) -> ChunkResponse:
    """添加单个简历 chunk，嵌入并存储到 pgvector。"""
    vs = VectorStore(db_session=db)
    result = await vs.add_chunk(req.user_id, req.chunk_type, req.content)
    return ChunkResponse(chunk_id=result["chunk_id"], embedding_dim=result["embedding_dim"])


@router.post("/ingest", response_model=list[ChunkResponse], status_code=201, dependencies=[Depends(verify_api_key)])
async def ingest_resume(
    req: ResumeIngestRequest, db: AsyncSession = Depends(get_db)
) -> list[ChunkResponse]:
    """上传完整简历文本，自动切块并向量化写入 pgvector。"""
    vs = VectorStore(db_session=db)
    chunks = await vs.chunk_resume(req.resume_text)

    results: list[ChunkResponse] = []
    for i, chunk in enumerate(chunks):
        chunk_type = "experience" if i < len(chunks) // 2 else "project"
        result = await vs.add_chunk(req.user_id, chunk_type, chunk)
        results.append(
            ChunkResponse(chunk_id=result["chunk_id"], embedding_dim=result["embedding_dim"])
        )
    return results
