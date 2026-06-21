# JobHunt-Flow — 架构深度解析

> 面向 Claude Code 的技术设计文档。所有组件有精确文件路径、接口签名和依赖关系。

---

## 1. 设计决策记录 (ADR)

每条决策附带理由，Claude Code 无需重新论证。

| ID | 决策 | 替代方案 | 理由 |
|----|------|----------|------|
| ADR-001 | **LangGraph** 而非 raw Hermes delegate_task | Hermes 子智能体 | 图状态机天然支持节点回滚、Human-in-the-loop、并行分支。Hermes delegate_task 是线性/扇出式，不适合复杂状态流转 |
| ADR-002 | **PostgreSQL + pgvector** 而非 ChromaDB + SQLite | ChromaDB | 向量检索 + 关系型数据同库，零运维心智负担。pgvector IVFFlat 索引在 10 万级 chunk 下性能足够 |
| ADR-003 | **Next.js** 而非 Vite+React | Vite+React | 前端也需要共享 API 路由 + 类型系统，且 Chrome Extension 与 frontend 共享同一套 shadcn/ui 组件体系 |
| ADR-004 | **Chrome Extension** 而非 Playwright 全自动 | Playwright | DOM 结构频繁变更，Playwright 维护成本接近重写。Extension 走 Content Script 注入，与页面解耦 |
| ADR-005 | **模型分层路由**而非单一模型 | 全用 GPT-4o-mini | 初筛 workload 占 80%，用免费/低成本模型可节省 90% API 费用。仅 Top 20% 需要深度分析 |
| ADR-006 | **TF-IDF 模糊去重**而非 raw_hash | exact hash | 同一岗位标题/内容微小差异重发极常见，raw_hash 漏判率高 |

---

## 2. 目录结构与文件契约

每个文件标注「职责」和「依赖（构建该文件前必须先完成的文件）」。

### 2.1 Phase 1 — 骨架 (目标: 可运行 `/match` 端点)

```
backend/
├── pyproject.toml                    # 依赖声明
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI 入口, lifespan, CORS
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py                # SQLAlchemy async session
│   │   └── models/                   # SQLAlchemy ORM
│   │       ├── __init__.py
│   │       ├── job.py                # jobs 表 ORM
│   │       ├── application.py        # applications 表 ORM
│   │       ├── user.py               # users 表 ORM
│   │       └── resume_chunk.py       # resume_chunks 表 ORM
│   ├── schemas/                      # Pydantic v2 — API 请求/响应
│   │   ├── __init__.py
│   │   ├── job.py
│   │   ├── match.py                  # ← Matcher 输出 (Structured Output target)
│   │   └── application.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── jobs.py                   # GET/POST /api/jobs
│   │   ├── applications.py           # GET/POST /api/applications
│   │   └── match.py                  # POST /api/match ← Phase 1 MVP
│   └── services/
│       ├── __init__.py
│       ├── matcher.py                # LLM 匹配逻辑
│       └── vector_store.py           # pgvector CRUD
```

依赖链:
```
pyproject.toml
  → db/models/*.py
    → db/session.py
      → main.py
        → api/*.py
          → schemas/*.py
            → services/matcher.py
              → services/vector_store.py
```

### 2.2 Phase 2 — 智能体网络

```
backend/
└── app/
    ├── agents/
    │   ├── orchestrator.py           # LangGraph 图定义
    │   ├── scraper_node.py           # Scraper 节点
    │   ├── matcher_node.py           # Matcher 节点
    │   ├── tailor_node.py            # Tailor 节点
    │   └── tracker_node.py           # Tracker 节点
    └── services/
        ├── scraper.py                # 三重降级爬虫
        ├── dedup.py                  # TF-IDF 模糊去重
        └── tailor.py                 # 简历定制 (Structured Outputs)

frontend/
├── src/
│   ├── app/dashboard/                # 漏斗看板
│   ├── app/jobs/                     # 职位瀑布流
│   └── app/resume/                   # 简历版本管理
└── package.json
```

### 2.3 Phase 3 — 投递闭环

```
backend/
└── app/
    ├── api/extension.py              # Chrome Extension API
    └── agents/applicant_node.py      # Applicant 节点

extension/
├── manifest.json
├── popup/
│   ├── index.html
│   └── App.tsx                       # shadcn/ui 浮窗
├── content/
│   └── inject.ts                     # 剪贴板注入 + 预填浮窗
└── shared/
    └── types.ts                      # 与 frontend 共享
```

---

## 3. API 契约

### POST /api/match — Phase 1 MVP

```
Request:
{
  "resume_text": "string",      // 简历全文
  "jd_text": "string"           // JD 全文
}

Response:
{
  "job_id": "uuid",             // 自动创建/关联
  "match_score": 0.72,
  "confidence": 0.85,
  "dimensions": {
    "skills_match": 0.8,
    "experience_match": 0.7,
    "industry_match": 0.6,
    "culture_fit": 0.7
  },
  "strengths": ["5年Python后端经验与JD高度匹配"],
  "gaps": ["缺少K8s生产经验"],
  "suggestions": ["在项目经历中补充K8s相关实践"],
  "should_apply": true,
  "priority": "high"
}
```

### POST /api/resume/chunk — 简历向量化入库

```
Request:
{
  "user_id": "uuid",
  "resume_text": "string"       // 简历全文，服务端自动 chunk + embed
}

Response:
{
  "chunks_created": 12,
  "status": "ok"
}
```

### GET /api/jobs?status=matched&limit=20 — 职位流

```
Response:
{
  "items": [
    {
      "id": "uuid",
      "title": "高级后端工程师",
      "company": "字节跳动",
      "match_score": 0.72,
      "application_status": "matched"
    }
  ],
  "total": 45,
  "page": 1
}
```

### POST /api/ext/task — Chrome Extension 投递任务

```
Request:
{
  "application_id": "uuid"
}

Response:
{
  "task_id": "uuid",
  "resume_url": "https://...",
  "cover_letter": "尊敬的HR...",
  "prefill_data": {
    "name": "张三",
    "email": "...",
    "phone": "..."
  },
  "expires_in": 3600
}
```

---

## 4. LangGraph 状态图

```
from typing import Literal, TypedDict
import operator

class AgentState(TypedDict):
    jobs_to_process: list[str]       # 待处理 job_id 队列
    current_job: str | None          # 当前处理中的 job_id
    status: Literal[
        "init", "scraping", "scraped",
        "matching", "matched",
        "tailoring", "tailored",
        "applying", "applied",
        "error", "rollback"
    ]
    errors: list[dict]               # [{job_id, node, error, timestamp}]
    pending_approval: list[str]      # 等待用户确认的 job_id
    metrics: dict                     # 运行时统计

# 图定义 (LangGraph)
graph = StateGraph(AgentState)

graph.add_node("scraper", scraper_node)
graph.add_node("matcher", matcher_node)
graph.add_node("tailor", tailor_node)
graph.add_node("applicant", applicant_node)
graph.add_node("tracker", tracker_node)

graph.add_edge("scraper", "matcher")
graph.add_conditional_edges(
    "matcher",
    decide_next,              # → tailor / notify_user / skip
    {"tailor": "tailor", "notify": END, "skip": END}
)
graph.add_conditional_edges(
    "tailor",
    decide_apply,             # → applicant / pending_approval
    {"apply": "applicant", "pending": END}
)
graph.add_edge("applicant", "tracker")
graph.add_edge("tracker", END)
```

---

## 5. RAG 匹配流程 (Matcher 核心)

```
输入: JD 全文
          │
          ▼
步骤1: 提取技能关键词 (本地 regex)
          │
          ▼
步骤2: 关键词 → pgvector cosine similarity search
          │  → 召回 resume_chunks 中最相关的 3-5 条
          │  → WHERE user_id = ? ORDER BY embedding <=> ? LIMIT 5
          ▼
步骤3: 拼接 Prompt:
          """
          你是资深招聘顾问。根据候选人的以下经历片段，评估与 JD 的匹配度。

          候选人的相关经历:
          {chunk_1}
          {chunk_2}
          {chunk_3}

          职位描述:
          {jd_text}

          按以下 JSON Schema 输出匹配报告...
          """
          │
          ▼
步骤4: 低成本模型初筛 (Gemini / Hermes 自带)
          │  → match_score < 0.5 → 直接返回
          │  → match_score ≥ 0.5 → 进入深度分析
          ▼
步骤5: 高成本模型深度 Gap 分析 (GPT-4o-mini)
          │  → 完整匹配报告 + 优化建议
          ▼
          输出至 applications 表
```

---

## 6. Tailor 结构化输出 Schema

```python
from pydantic import BaseModel, Field
from typing import Literal

class SectionModification(BaseModel):
    """单段经历的修改方案"""
    original_text: str = Field(description="简历原文中的段落")
    modified_text: str = Field(description="修改后的段落")
    change_reason: str = Field(description="为什么这样改，对应 JD 的哪条要求")
    is_factual: bool = Field(
        description="True=基于原文改写，False=新增内容（必须标注）"
    )

class TailorOutput(BaseModel):
    """Tailor Agent 的强制结构化输出"""
    sections_to_modify: list[SectionModification] = Field(
        description="需要修改的段落列表，每段独立标注"
    )
    sections_to_keep: list[str] = Field(
        description="不需要修改的段落原文（防止模型擅自删除）"
    )
    cover_letter: str = Field(description="针对该 JD 的求职信")
    verification_note: str = Field(
        description="模型自检声明：确认没有编造任何经历"
    )
```

---

## 7. 异常恢复协议

每个 Agent 节点必须实现以下错误处理：

```python
def agent_node(state: AgentState) -> AgentState:
    try:
        # ... 实际业务逻辑
        pass
    except (LLMOutputError, NetworkError, ValidationError) as e:
        # 1. 记录错误
        state["errors"].append({
            "job_id": state["current_job"],
            "node": "matcher",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        # 2. 状态回滚
        db.rollback_application(state["current_job"])
        # 3. 尝试降级
        if isinstance(e, LLMOutputError):
            result = use_fallback_tfidf(state["current_job"])
        elif isinstance(e, NetworkError):
            state["jobs_to_process"].append(state["current_job"])  # 重试队列
        # 4. 状态迁移
        state["status"] = "error"
        return state
```

---

## 8. Chrome Extension 数据流

```
[Backend]                         [Browser]                     [User]
   │                                │                            │
   ├─ POST /api/ext/task ──────────►│                            │
   │  ← {task_id, prefill_data}    │                            │
   │                                ├─ content/inject.ts         │
   │                                │  → 检测到投递表单页面       │
   │                                │  → 注入浮动浮窗            │
   │                                │    ┌──────────────────┐   │
   │                                │    │  🎯 一键投递助手   │   │
   │                                │    │                   │   │
   │                                │    │ 姓名: 张三 ✓     │   │
   │                                │    │ 电话: 138... ✓   │   │
   │                                │    │ 简历: v2.3 ✓     │   │
   │                                │    │                   │   │
   │                                │    │ [确认投递] [取消]  │   │
   │                                │    └──────────────────┘   │
   │                                │                            │
   │                                │◄──── 用户点击确认 ─────── │
   │                                ├─ 自动填入表单              │
   │                                ├─ 留空 Submit 按钮         │
   │                                │  （用户手动点击，反爬）    │
   │  ← POST /api/ext/complete ────┤                            │
```
