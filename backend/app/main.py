"""JobHunt-Flow FastAPI 入口。

启动:
    uv run uvicorn app.main:app --reload
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import init_db
import app.db.models  # noqa: F401 — registers all ORM models with Base.metadata
from app.api.match import router as match_router
from app.api.jobs import router as jobs_router
from app.api.applications import router as applications_router
from app.api.agents import router as agents_router
from app.api.extension import router as extension_router
from app.api.resume import router as resume_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库表。"""
    await init_db()
    yield


app = FastAPI(
    title="JobHunt-Flow",
    description="高可用多智能体求职系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(match_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(agents_router)
app.include_router(extension_router)
app.include_router(resume_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
