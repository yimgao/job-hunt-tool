# JobHunt-Flow — Claude Code 分阶段构建指南

> 本文档是 Claude Code 的执行蓝图。每个 Phase 标注了精确的文件创建顺序、依赖关系和验证步骤。

---

## 构建总纲

```
Phase 1: 骨架 + MVP /match 端点    → 可运行后端 + LLM 匹配
Phase 2: 智能体网络 + 前端         → LangGraph + Next.js Dashboard
Phase 3: 投递闭环 + Extension     → Chrome Extension + 自动编排
Phase 4: 增强 + 成本优化           → RAG 调优、降级策略、批量部署
```

**Golden Rule**: 每个 Phase 结束时必须有可验证的产物。不跳过验证。

---

## Phase 1 — 骨架 + MVP（目标: 可运行 `POST /api/match`）

> 无前后端依赖。纯后端 + LLM 匹配验证。

### 文件创建顺序

```
Step 1:  pyproject.toml
Step 2:  app/__init__.py
Step 3:  app/db/__init__.py
Step 4:  app/db/session.py          ← SQLAlchemy async engine + session
Step 5:  app/db/models/user.py
Step 6:  app/db/models/job.py
Step 7:  app/db/models/application.py
Step 8:  app/db/models/resume_chunk.py
Step 9:  app/db/models/__init__.py  ← 聚合所有 model
Step 10: app/schemas/__init__.py
Step 11: app/schemas/job.py
Step 12: app/schemas/match.py       ← Matcher 输出 Schema (结构化输出目标)
Step 13: app/schemas/application.py
Step 14: app/services/__init__.py
Step 15: app/services/vector_store.py
Step 16: app/services/matcher.py    ← LLM 匹配核心逻辑
Step 17: app/api/__init__.py
Step 18: app/api/match.py           ← POST /api/match
Step 19: app/main.py                ← FastAPI 入口 + lifespan + CORS
```

### Step-by-step 规格

#### Step 1: `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "jobhunt-flow"
version = "0.1.0"
description = "高可用多智能体求职系统"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "scikit-learn>=1.0.0",
    "numpy>=1.24.0",
    "httpx>=0.26.0",
    "openai>=1.6.0",          # 通用 LLM 客户端
    "langgraph>=0.0.30",       # Phase 2 用，提前声明避免冲突
    "pgvector>=0.2.0",
]

[project.scripts]
jobhunt = "app.main:start_cli"

[tool.hatch.build.targets.wheel]
packages = ["app/"]
```

#### Step 4: `app/db/session.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobhunt"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

#### Step 12: `app/schemas/match.py` — Matcher 结构化输出目标

```python
from pydantic import BaseModel, Field

class MatchDimensions(BaseModel):
    skills_match: float = Field(ge=0, le=1)
    experience_match: float = Field(ge=0, le=1)
    industry_match: float = Field(ge=0, le=1)
    culture_fit: float = Field(ge=0, le=1)

class MatchReport(BaseModel):
    """Matcher Agent 的结构化输出。也是 LLM Structured Outputs 的 target schema。"""
    job_id: str
    match_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    dimensions: MatchDimensions
    strengths: list[str]
    gaps: list[str]
    suggestions: list[str]
    should_apply: bool
    priority: str = Field(pattern="^(high|medium|low)$")

class MatchRequest(BaseModel):
    resume_text: str = Field(min_length=50)
    jd_text: str = Field(min_length=50)

class MatchResponse(BaseModel):
    report: MatchReport
    report_id: str
    llm_model: str
    llm_cost: float
```

#### Step 16: `app/services/matcher.py`

```python
"""LLM 匹配逻辑。先 RAG 召回 → 低成本初筛 → 高成本深度分析。"""

from openai import AsyncOpenAI
from app.schemas.match import MatchReport

class MatcherService:
    def __init__(self, api_key: str, vector_store=None):
        self.client = AsyncOpenAI(api_key=api_key)
        self.vector_store = vector_store

    async def quick_scan(self, chunks: list[str], jd_text: str) -> dict:
        """低成本模型初筛。返回 match_score + reason"""
        prompt = f"..."
        resp = await self.client.chat.completions.create(
            model="gpt-4o-mini",  # 或替换为 Gemini free tier
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return resp.choices[0].message.content

    async def deep_analyze(self, chunks: list[str], jd_text: str) -> MatchReport:
        """高成本模型深度分析。返回结构化 MatchReport"""
        prompt = f"..."
        resp = await self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format=MatchReport
        )
        return resp.choices[0].message.parsed

    async def match(self, resume_text: str, jd_text: str) -> MatchReport:
        """完整匹配流程"""
        # 1. 从 resume chunk 召回（若 vector_store 可用）
        chunks = await self.vector_store.search(resume_text) if self.vector_store else [resume_text[:2000]]

        # 2. 初筛
        quick = await self.quick_scan(chunks, jd_text)
        score = float(quick.get("match_score", 0))

        # 3. 低分直接返回
        if score < 0.5:
            return MatchReport(
                job_id="", match_score=score, confidence=0.7,
                dimensions=..., strengths=[], gaps=[], suggestions=[],
                should_apply=False, priority="low"
            )

        # 4. 高分深度分析
        return await self.deep_analyze(chunks, jd_text)
```

#### Step 18: `app/api/match.py`

```python
from fastapi import APIRouter, Depends
from app.schemas.match import MatchRequest, MatchResponse
from app.services.matcher import MatcherService

router = APIRouter(prefix="/api", tags=["match"])

@router.post("/match", response_model=MatchResponse)
async def match_job(req: MatchRequest):
    """简历 vs JD 匹配分析。Phase 1 MVP 端点。"""
    service = MatcherService(api_key="...")
    report = await service.match(req.resume_text, req.jd_text)
    return MatchResponse(
        report=report,
        report_id="...",
        llm_model="gpt-4o-mini",
        llm_cost=0.002
    )
```

#### Step 19: `app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import init_db
from app.api.match import router as match_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # 启动时建表
    yield

app = FastAPI(title="JobHunt-Flow", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(match_router)
```

### Phase 1 验证清单

```
[ ] cd backend && uv venv && source .venv/bin/activate
[ ] uv pip install -e ".[dev]"
[ ] createdb jobhunt (PostgreSQL)
[ ] uv run uvicorn app.main:app --reload
[ ] curl -X POST http://localhost:8000/api/match \
      -H "Content-Type: application/json" \
      -d '{"resume_text": "...", "jd_text": "..."}'
[ ] 返回 200 + 完整 MatchReport
```

---

## Phase 2 — 智能体网络 + 前端

> 构建 LangGraph 编排层 + Next.js 前端。

### 后端新增文件

```
backend/
└── app/
    ├── agents/
    │   ├── __init__.py
    │   ├── orchestrator.py          ← LangGraph StateGraph
    │   ├── scraper_node.py
    │   ├── matcher_node.py
    │   ├── tailor_node.py           ← 结构化输出 (Pydantic TailorOutput)
    │   └── tracker_node.py
    ├── services/
    │   ├── scraper.py               ← 三重降级爬虫
    │   ├── dedup.py                 ← TF-IDF 模糊去重
    │   ├── tailor.py                ← 简历定制逻辑
    └── api/
        ├── jobs.py                  ← GET/POST /api/jobs
        ├── applications.py          ← GET/POST /api/applications
        └── agents.py               ← POST /api/agents/run
```

### 前端文件

```
frontend/
├── package.json                     ← next@14, react@18, tailwind, shadcn/ui
├── tsconfig.json
├── next.config.js
├── tailwind.config.ts
├── src/
│   ├── app/
│   │   ├── layout.tsx               ← 全局布局 (shadcn ThemeProvider)
│   │   ├── page.tsx                 ← redirect → /dashboard
│   │   ├── dashboard/
│   │   │   ├── page.tsx             ← 漏斗看板 (funnel chart)
│   │   │   └── components/
│   │   │       ├── FunnelChart.tsx
│   │   │       └── StatsCards.tsx
│   │   ├── jobs/
│   │   │   ├── page.tsx             ← 职位瀑布流
│   │   │   └── components/
│   │   │       └── JobCard.tsx
│   │   └── resume/
│   │       └── page.tsx             ← 简历版本管理
│   ├── lib/
│   │   ├── api.ts                   ← fetch wrapper
│   │   └── types.ts                 ← 与 backend schemas 对应
│   └── components/
│       └── ui/                      ← shadcn/ui 组件
```

### Orchestrator (LangGraph) 核心

```python
# app/agents/orchestrator.py
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)
workflow.add_node("scraper", scraper_node)
workflow.add_node("matcher", matcher_node)
workflow.add_node("tailor", tailor_node)
workflow.add_node("tracker", tracker_node)

workflow.add_conditional_edges(
    "matcher",
    decide_next,                     # → tailor / notify / skip
    {"tailor": "tailor", "notify": END, "skip": END}
)
workflow.set_entry_point("scraper")
workflow.add_edge("tailor", "tracker")
workflow.add_edge("tracker", END)
```

### Phase 2 验证清单

```
[ ] uv run uvicorn app.main:app --reload  (后端正常)
[ ] POST /api/agents/run 触发一次全管道
[ ] GET /api/jobs?limit=5 返回职位列表
[ ] GET /api/applications?status=matched 返回投递记录
[ ] cd frontend && pnpm install && pnpm dev  (前端正常)
[ ] http://localhost:3000/dashboard 显示漏斗图表
```

---

## Phase 3 — 投递闭环 + Extension

### 新增文件

```
backend/
└── app/
    ├── agents/applicant_node.py     ← 投递准备 + Extension 任务创建
    └── api/extension.py            ← POST /api/ext/task, /api/ext/complete

extension/
├── manifest.json                    ← permissions: storage, clipboard, activeTab
├── popup/
│   ├── index.html
│   └── App.tsx                      ← shadcn 浮窗, 显示预填数据
├── content/
│   └── inject.ts                    ← 检测投递表单 + 注入浮窗
└── shared/
    └── types.ts                    ← ExtensionTask, PrefillData
```

### Phase 3 验证清单

```
[ ] POST /api/ext/task 返回 task_id + prefill_data
[ ] Chrome 加载 extension，导航到招聘网站
[ ] Extension 浮窗弹出，显示预填数据
[ ] 用户点击确认，表单字段自动填入
[ ] POST /api/ext/complete 投递完成
[ ] GET /api/applications?status=applied 显示已投递
```

---

## Phase 4 — 增强 + 成本优化

### 优化项

| 优先级 | 优化 | 文件 | 收益 |
|--------|------|------|------|
| P0 | RAG 调优: embedding 模型对比测试 | `services/vector_store.py` | 匹配召回率 + 20% |
| P0 | LLM 路由策略: Gemini free tier 初筛 | `services/matcher.py` | API 成本 -80% |
| P1 | 异常恢复: 重试队列 + 状态回滚 | `agents/orchestrator.py` | 系统可靠性 |
| P1 | 缓存层: Redis 职位去重缓存 | `services/dedup.py` | 去重速度 10x |
| P2 | Hermes cron 注册: 每日自动扫描 | `scripts/daily_scan.sh` | 全自动运营 |
| P2 | 通知通道: Telegram bot | `services/notifier.py` | 用户即时感知 |

### 成本验证

```bash
# 运行 100 次 match 并统计
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/match -d '{"resume_text":"...","jd_text":"..."}'
done
# 检查日志中的 llm_cost 总和
# 目标: 100 次 < $1.00
```

---

## 目录结构最终形态

```
jobhunt-flow/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── match.py
│   │   │   ├── jobs.py
│   │   │   ├── applications.py
│   │   │   ├── agents.py
│   │   │   └── extension.py
│   │   ├── models/
│   │   │   ├── job.py
│   │   │   ├── application.py
│   │   │   ├── user.py
│   │   │   └── resume_chunk.py
│   │   ├── schemas/
│   │   │   ├── match.py
│   │   │   ├── tailor.py
│   │   │   ├── job.py
│   │   │   └── application.py
│   │   ├── services/
│   │   │   ├── matcher.py
│   │   │   ├── scraper.py
│   │   │   ├── tailor.py
│   │   │   ├── dedup.py
│   │   │   └── vector_store.py
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── scraper_node.py
│   │   │   ├── matcher_node.py
│   │   │   ├── tailor_node.py
│   │   │   ├── applicant_node.py
│   │   │   └── tracker_node.py
│   │   └── db/
│   │       ├── session.py
│   │       └── migrations/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/app/{dashboard,jobs,resume,settings}/
│   └── package.json
├── extension/
│   ├── manifest.json
│   ├── popup/
│   ├── content/
│   └── shared/
├── scripts/
│   ├── daily_scan.sh
│   └── apply_pipeline.sh
├── doc/
│   ├── ARCHITECTURE.md
│   ├── AGENTS.md
│   └── IMPLEMENTATION.md
└── README.md
```
