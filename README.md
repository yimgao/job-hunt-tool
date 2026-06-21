# 🎯 JobHunt-Flow

> **高可用多智能体求职系统** — 图编排 + RAG 匹配 + 半自动投递，驻留在 Hermes 上的 AI 猎头。

```text
爬取 → 去重 → RAG召回 → LLM评分 → 定制简历 → 半自动投递 → 漏斗追踪
                                        ↕
                                Chrome Extension 一键确认
```

---

## 核心设计原则

| 原则 | 说明 |
|------|------|
| **Graph-based Orchestration** | LangGraph/CrewAI 驱动的图状态机，天然支持异常捕获、状态回滚与 Human-in-the-loop |
| **RAG & Rerank 优先** | 简历分块向量化，按 JD 动态召回相关片段，拒绝暴力全量塞 prompt |
| **防御性 AI 工程** | 所有内容修改 Agent 强制绑定 Structured Outputs（Pydantic Schema） |
| **半自动投递** | Chrome Extension 预填 → 用户肉眼确认 → 一键提交，绕开 DOM 逆向深水区 |
| **零预算友好** | 免费 Embedding + 免费初筛模型 + 本地 TF-IDF 去重，日均 < $0.30 |

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                 Multi-Agent Orchestration Layer                  │
│                      (LangGraph / CrewAI)                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                 Orchestrator Agent                      │     │
│  │  · 状态图流转 (Init→Scraped→Matched→Tailored→Applied)   │     │
│  │  · 全局异常捕获与状态回滚 (Rollback mechanism)           │     │
│  └──────┬──────────┬──────────┬──────────┬──────────┬──────┘     │
│         │          │          │          │          │            │
│  ┌──────┴┐ ┌──────┴┐ ┌──────┴┐ ┌──────┴┐ ┌──────┴┐           │
│  │Scraper│ │Matcher│ │Tailor │ │Applic.│ │Tracker│           │
│  │(三重降级)│ │(RAG赋能)│ │(强结构化)│ │(半自动)│ │(漏斗统计)│           │
│  └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘           │
└──────┼─────────┼─────────┼─────────┼─────────┼───────────────┘
       │         │         │         │         │
┌──────┴─────────┴─────────┴─────────┴─────────┴───────────────┐
│                    Backend (FastAPI)                          │
│  ┌───────────────┐ ┌──────────────┐ ┌───────────────────┐    │
│  │  Job/App API  │ │  Agent API   │ │ Chrome Ext. API   │    │
│  └──────┬────────┘ └──────┬───────┘ └────────┬──────────┘    │
│         │                 │                   │               │
│  ┌──────┴─────────────────┴───────────────────┴──────────┐   │
│  │                 DB Layer                               │   │
│  │  · PostgreSQL (jobs, apps, users, logs)                │   │
│  │  · pgvector   (resume chunks embeddings)               │   │
│  │  · Redis      (text dedup hash cache)                  │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│                    Frontend (Next.js)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │Dashboard │ │ Job Feed │ │  Resume  │ │ Browser Ext.   │  │
│  │ (漏斗看板)│ │ (职位瀑布)│ │ (简历版本)│ │ (一键投递助手)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 编排 | LangGraph / CrewAI | 图状态机，节点级异常捕获 + Human-in-the-loop |
| 后端 | FastAPI + Pydantic v2 | 异步原生，结构化输出强制约束 |
| 前端 | Next.js 14 (App Router) | 服务端渲染 + API 路由 + 浏览器扩展共享类型 |
| 数据库 | PostgreSQL + pgvector | 关系型 + 向量检索一体化，省运维 |
| 缓存/去重 | Redis | 高速文本哈希判断 |
| LLM 路由 | Gemini (初筛) → GPT (深度) | 成本最优 |
| 投递 | Chrome Extension (React) | 比 Playwright 稳定 10 倍 |
| Embedding | text-embedding-3-small / bge-small | 免费/极低成本 |

---

## 目录结构

```
jobhunt-flow/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── api/
│   │   │   ├── jobs.py             # /api/jobs     — 职位 CRUD
│   │   │   ├── applications.py     # /api/apps     — 投递 CRUD
│   │   │   ├── agents.py           # /api/agents   — 智能体控制
│   │   │   └── extension.py        # /api/ext      — Chrome 扩展接口
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── job.py
│   │   │   ├── application.py
│   │   │   ├── user.py
│   │   │   └── resume_chunk.py
│   │   ├── schemas/                # Pydantic v2 schemas
│   │   │   ├── job.py
│   │   │   ├── match.py            # Matcher 输出 schema
│   │   │   ├── tailor.py           # Tailor 输出 schema (强约束)
│   │   │   └── application.py
│   │   ├── services/
│   │   │   ├── matcher.py          # RAG + LLM 匹配
│   │   │   ├── scraper.py          # 三重降级爬虫
│   │   │   ├── tailor.py           # 结构化输出简历定制
│   │   │   ├── dedup.py            # TF-IDF 模糊去重
│   │   │   └── vector_store.py     # pgvector CRUD
│   │   ├── agents/                 # LangGraph node 定义
│   │   │   ├── orchestrator.py     # 图状态机
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
│
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router
│   │   │   ├── dashboard/          # 漏斗看板
│   │   │   ├── jobs/               # 职位瀑布流
│   │   │   ├── resume/             # 简历版本管理
│   │   │   └── settings/           # 用户配置
│   │   ├── components/             # shadcn/ui 组件
│   │   └── lib/
│   │       ├── api.ts              # API client
│   │       └── types.ts            # 共享类型
│   └── package.json
│
├── extension/                      # Chrome Extension
│   ├── manifest.json
│   ├── popup/
│   ├── content/
│   └── shared/                     # 与 frontend 共享类型
│
├── scripts/                        # Hermes cron 入口
│   ├── daily_scan.sh
│   └── apply_pipeline.sh
│
├── doc/
│   ├── ARCHITECTURE.md             # ← 本文件
│   ├── AGENTS.md                   # 智能体详细设计
│   ├── IMPLEMENTATION.md           # CC 分阶段构建指南
│   └── COST.md                     # 成本控制面板
│
└── README.md
```

---

## 数据流

```
[Scraper Agent]
  每日 Cron 触发 → 三重降级爬取 BOSS/LinkedIn/Indeed
  → TF-IDF 模糊去重（相似度 >95% 丢弃）
  → 写入 jobs 表
       │
       ▼
[Orchestrator 调度]
  → 遍历新职位，逐条 delegate_task 给 Matcher
       │
       ▼
[Matcher Agent]
  1. 从 JD 提取核心技能关键词
  2. Vector DB 召回简历中最相关的 3-5 个项目 chunk
  3. 低成本模型初筛（batch 50 个）
  4. 高分候选 → 高成本模型深度 Gap 分析
  → 输出匹配报告写入 applications
       │
       ├── 匹配度 < 30% → 跳过
       ├── 30-60%      → Dashboard 推送
       └── ≥ 60%       → 自动进入 Tailor 队列
                           │
                           ▼
              [Tailor Agent]
              1. 强制 Structured Outputs (Pydantic)
              2. Thought Signature 约束（事实比对再改写）
              3. 生成定制简历 + 求职信
              → 写入 application.tailored_resume_url
                           │
                           ▼
              [Chrome Extension 唤醒]
              用户浏览器侧栏弹出 → 预填数据 + 剪贴板注入
              → 用户肉眼确认 → 手动点击 Submit
                           │
                           ▼
              [Tracker Agent]
              更新 applications.status → Dashboard 漏斗刷新
```

---

## 数据库设计

```sql
-- 职位表 (TF-IDF 内容哈希去重)
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,               -- BOSS直聘 / LinkedIn / Indeed
    source_id TEXT UNIQUE,              -- 平台原始 ID
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    salary_min INT,
    salary_max INT,
    jd_text TEXT NOT NULL,
    skills JSONB,                       -- JSONB 提升查询效率
    content_hash TEXT UNIQUE,           -- TF-IDF 清洗后哈希（去重用）
    url TEXT,
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 简历向量库 (RAG)
CREATE TABLE resume_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    chunk_type TEXT NOT NULL,            -- experience / education / project
    content TEXT NOT NULL,
    embedding vector(768),              -- pgvector 扩展
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_resume_chunks_user ON resume_chunks(user_id);
CREATE INDEX idx_resume_chunks_embedding ON resume_chunks
    USING ivfflat (embedding vector_cosine_ops);

-- 投递状态机
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id),
    user_id UUID NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'scraped'
        CHECK (status IN ('scraped','matched','tailored','applied','rejected','archived')),
    match_score FLOAT,
    match_report JSONB,                 -- Matcher 完整输出
    tailored_resume_url TEXT,           -- 定制简历存储地址
    tailored_cover_letter TEXT,
    extension_task_id TEXT,             -- Chrome Extension 任务 ID
    error_log TEXT,                     -- Agent 失败原因日志
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 用户画像
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    email TEXT UNIQUE,
    resume_text TEXT,                   -- 当前完整简历
    preferences JSONB,                  -- 目标薪资/地点/行业/技能
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 成本控制

| 环节 | 策略 | 单次耗时 | 成本 |
|------|------|----------|------|
| 职位获取 | RSS / 平台轻量 API | < 1s | $0.00 |
| 相似度去重 | 本地 TF-IDF (scikit-learn) | < 50ms | $0.00 |
| RAG 向量化 | 开源 Embedding (bge-small) | < 100ms | $0.00 |
| 大规模初筛 | Gemini free tier / Hermes 自带模型 | 2-4s | $0.00 |
| 深度定制分析 | GPT-4o-mini Structured Outputs | 10-15s | ~$0.02-0.05/次 |
| **日均 100 职位，精筛 5 个** | — | — | **< $0.30** |

---

## 许可证

MIT
