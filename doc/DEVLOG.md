# DEVLOG — JobHunt-Flow 开发日志

> 记录从零到完整多智能体求职系统的构建过程。

---

## Phase 0 — 项目立项与脚手架

**目标**: 确定技术栈，建立开发规范，搭建最小可运行骨架。

**决策**:
- 编排层选 **LangGraph 1.2.6**（StateGraph + conditional_edges 支持复杂分支）
- LLM 路由: Gemini 1.5 Flash（免费额度初筛）→ GPT-4o-mini（深度分析），日均成本目标 < $0.30
- DB: PostgreSQL 16 + pgvector（向量检索）+ Redis（L1 去重缓存）
- 前端投递: Chrome Extension MV3（半自动，用户确认后提交）
- 包管理: `uv`（比 pip 快 10-100x，锁文件确定性）

**产出**:
- `pyproject.toml` — 项目元数据
- `.gitignore` — 排除 `.venv/`, `*.pyc`, `dist/`, `.coverage`
- `CLAUDE.md` — 给 AI 协作者的操作规范
- `README.md` — 项目概述
- `doc/` — 架构、智能体、实施、成本文档
- `.github/prompts/` — plan / tdd / refactor / build-fix prompt 模板

---

## Phase 1 — 基础设施与数据层

**目标**: 让数据库跑起来，定义 ORM 模型。

### 基础设施 (docker-compose.yml)

```
postgres (pgvector/pgvector:pg16) :5432
redis (redis:7-alpine)            :6379
```

两个服务都加了 healthcheck，postgres 数据持久化到 named volume。

### ORM 模型 (SQLAlchemy async)

| 模型 | 表 | 关键字段 |
|------|-----|---------|
| `Job` | `jobs` | `source_id` (unique), `content_hash` (unique), `jd_text` |
| `Application` | `applications` | FK → jobs, status ENUM |
| `User` | `users` | email unique |
| `ResumeChunk` | `resume_chunks` | `Vector(1536)` pgvector 列 |

**关键问题 & 解决**:
- `init_db()` 创建表失败 → 原因：models 未在 `create_all` 前 import。在 `main.py` 加 `import app.db.models` 修复。
- `ResumeChunk.embedding` 从 `ARRAY(Float)` 占位符换成 `pgvector.sqlalchemy.Vector(1536)`。
- `session.py` 在 `create_all` 前执行 `CREATE EXTENSION IF NOT EXISTS vector`。

---

## Phase 2 — FastAPI 后端 + 核心 API

**目标**: RESTful CRUD + LLM 匹配端点，可独立测试。

### 应用工厂 (main.py)

- `lifespan` 上下文管理器: 启动时 `init_db()`，优雅关闭
- CORS 全放行（开发阶段），生产需收紧
- `AsyncClient` (httpx) 作为测试客户端，非 `TestClient`

### Jobs & Applications API

```
GET  /api/jobs            — list with limit/offset/source filters
GET  /api/jobs/{id}
POST /api/jobs            — create with content_hash dedup (409 on dup)
GET  /api/applications
GET  /api/applications/{id}
PATCH /api/applications/{id} — status update
```

**关键问题 & 解决**:
- `GET /api/jobs` 返回 500 → `JobResponse.id: str` 无法接收 `uuid.UUID`（Pydantic v2 `from_attributes` 模式下不自动强转）。改成 `id: uuid.UUID` 解决。
- `POST /api/jobs` 重复 source_id 返回 500 → 捕获 `sqlalchemy.exc.IntegrityError` → 返回 409。

### Match API

```
POST /api/match  — 接收 resume_text + jd_text，返回 MatchReport
```

- `MatchReport` Pydantic schema: `match_score`, `strengths`, `gaps`, `recommendation`, `priority`
- LLM Structured Output 用 `client.beta.chat.completions.parse()` + `response_format=MatchReport`

### 服务层

- `matcher.py` — Gemini 快速初筛（`quick_scan`）→ GPT-4o-mini 深度分析（`deep_analyze`），双层降级
- `tailor.py` — 定制简历 + cover letter，Structured Output 输出 `TailoredOutput`
- `scraper.py` — 示例数据抓取，TF-IDF 内容去重（scikit-learn `TfidfVectorizer` + `cosine_similarity`）
- `dedup.py` — `TFIDFDeduplicator`（in-process 模糊去重）+ `RedisHashCache`（跨重启精确去重）

---

## Phase 3 — LangGraph 多智能体编排

**目标**: 五节点流水线端到端跑通。

### 图结构

```
START → scraper_node → matcher_node ─[score≥0.6]→ tailor_node → applicant_node → tracker_node → END
                                    ─[0.3≤score<0.6]→ tracker_node → END
                                    ─[score<0.3]→ END
```

### 节点职责

| 节点 | 输入 | 输出 | 降级 |
|------|------|------|------|
| `scraper_node` | `resume_text` | `jobs`, `current_job` | 返回示例职位 |
| `matcher_node` | `current_job`, `resume_text` | `match_report`, `pipeline_status` | TF-IDF 回退 |
| `tailor_node` | `match_report`, `resume_text` | `tailored_resume`, `cover_letter` | 返回原文 |
| `applicant_node` | `match_report`, `current_job` | `application_id` (ExtensionTask) | 跳过投递 |
| `tracker_node` | `application_id` | `pipeline_status: done` | 记录日志 |

**AgentState** 用 `TypedDict(total=False)` 允许节点只更新关心的字段。

**关键问题 & 解决**:
- `pipeline_status: "skip"` 即使简历有效 → `scraper_node` 未在返回值里设置 `current_job`，`matcher_node` 看到 `None` 就 skip。在 scraper 返回值加 `"current_job": unique[0] if unique else None` 修复。

### Chrome Extension 任务队列 API

```
POST /api/ext/task          — 创建预填充任务 (201)
GET  /api/ext/task/{id}     — 查询任务状态
GET  /api/ext/tasks/pending — 轮询待处理任务
POST /api/ext/complete      — 标记完成
```

`applicant_node` 创建 `ExtensionTask`，Extension popup 10s 轮询 `/pending`，用户点击后触发 autofill。

---

## Phase 4 — 生产加固 (向量检索 / Redis / Gemini / Telegram)

**目标**: 降低 LLM 成本，增加系统可靠性，补完简历向量化。

### 向量简历存储 (pgvector)

```
POST /api/resume/chunks  — 单 chunk 嵌入存储
POST /api/resume/ingest  — 全文自动切块 + 向量化
```

- `VectorStore.embed()` 调用 `text-embedding-3-small`，失败返回零向量（不抛异常）
- `VectorStore.search()` 用 `cosine_distance()` pgvector 运算符，`threshold=0.6` 过滤
- `VectorStore.chunk_resume()` 按双换行分段，过滤 < 50 字符的段落，最多 20 块

### Gemini 路由（成本优化）

- `quick_scan` 优先用 Gemini 1.5 Flash（`generativelanguage.googleapis.com/v1beta/openai/` 兼容端点）
- Gemini 失败 → 自动 fallback GPT-4o-mini
- 两层都加 `@with_retry(max_retries=2)` 指数退避

### Redis L1 去重（`dedup.py`）

- `RedisHashCache` — `SADD jobhunt:seen_hashes` per job `content_hash`
- `scraper_node` 先查 Redis（O(1)），命中则跳过；未命中再做 TF-IDF L2 检查
- 好处：跨进程重启保留已见哈希

### Telegram 通知 (`notifier.py`)

| 场景 | 消息 |
|------|------|
| 新高匹配 (≥60%) | 🔥 职位名 @ 公司，匹配度，投递链接 |
| 投递完成 | ✅ 职位名 @ 公司 |
| Pipeline 异常 | ⚠️ 错误摘要 |
| 每日日报 | 📊 扫描数/匹配数/投递数/成本 |

未配置 `TELEGRAM_BOT_TOKEN` 时静默降级，不抛异常。

### Retry 工具 (`utils/retry.py`)

```python
@with_retry(max_retries=2, base_delay=1.0)
async def quick_scan(...): ...
```

指数退避: `sleep(base * 2^attempt)`，仅重试指定异常类型。

### 每日定时脚本 (`scripts/daily_scan.py`)

```bash
python scripts/daily_scan.py --resume-file /data/resume.txt
# crontab: 0 8 * * * cd /app && uv run python scripts/daily_scan.py --resume-file ...
```

---

## 测试策略

| 层级 | 工具 | 策略 |
|------|------|------|
| Unit | `pytest-asyncio` | mock LLM client，隔离 DB |
| API | `httpx.AsyncClient` + `ASGITransport` | patch `init_db` 跳过真实 DB |
| Integration | (未实现) | 需要 Docker postgres |

**85 tests passed, 81% coverage**（超过 80% 目标）

**关键 fixture 设计**:
- `conftest.py` 用 `AsyncClient(ASGITransport(app=app))` 而非 `TestClient`（支持 async endpoints）
- `task_store` 测试用 `autouse` fixture 在每个测试前后 `clear()`（避免状态污染）
- `VectorStore` 测试直接覆盖 `self.client` 属性（不 patch 模块级变量）

---

## 成本估算

| 操作 | 模型 | 估算成本 |
|------|------|---------|
| 初筛 (quick_scan) | Gemini 1.5 Flash | 免费 (60 req/min) |
| 深度分析 (deep_analyze) | GPT-4o-mini | ~$0.001/次 |
| Embedding | text-embedding-3-small | ~$0.00002/1K token |
| 每日 50 职位 | 混合路由 | ~$0.05-0.15/天 |

日均成本远低于 $0.30 目标。

---

## 技术债 & 后续（Phase 4 结束时）

- [ ] `/api/jobs` scraper 接入真实 LinkedIn / Indeed / Boss 直聘
- [ ] `GET /api/match` 结果缓存（Redis TTL 1h，相同 resume+JD hash 命中）
- [ ] Extension 支持多 Tab 并发填表
- [ ] Prometheus metrics + Grafana 监控 LLM 成本曲线
- [ ] 生产 CORS 收紧到具体域名
- [ ] 集成测试（Docker Compose 起 postgres/redis，跑端到端 pipeline）

---

## Phase 5 — 真实数据源 + 前端仪表盘 + DB 持久化

### 5A — 真实多源 Scraper（7 路并发）

**目标**: 替换 mock 数据，接入无需 auth 的公开 API。

#### 数据源架构

```
ScraperService.scrape()
  ├─ HNScraper         — Algolia API（HN "Who's Hiring" 月帖）
  ├─ RemoteOKScraper   — remoteok.com/api（JSON）
  ├─ WeWorkRemotelyScraper — RSS feed
  ├─ RemotiveScraper   — remotive.com/api/remote-jobs（REST）
  ├─ GreenhouseScraper — boards-api.greenhouse.io（55+ 公司）
  ├─ LeverScraper      — api.lever.co（2 个验证有效的 slug）
  └─ SmartRecruitersScraper — api.smartrecruiters.com（Canva/Palantir/Uber）
```

所有 scraper 继承 `ScraperBase`，通过 `asyncio.gather` 并发执行，`Semaphore(6)` 控制 ATS 类单公司并发。实测 100 个去重职位 / 14 秒。

#### 关键踩坑

| 问题 | 根因 | 修复 |
|------|------|------|
| Greenhouse 全返回 404 | URL 用了 `boards.greenhouse.io/api/v1/...` | 正确 URL: `boards-api.greenhouse.io/v1/boards/{slug}/jobs` |
| RemoteOK 匹配到非技术职位 | 平台把 50+ 站内 tag 都附到每条 job | 只取 `tags[:8]`（前 8 个是职位专属 tag）|
| HN Scraper 抓到 2015 年帖 | 搜索无日期过滤 | 加 `numericFilters=created_at_i>1700000000` |
| HN 欧洲职位泄漏 | 未排除 "eu only" / "europe only" 等 | 加排除词列表 |
| Lever 大量 404 | 大多数公司已迁走 Lever | 仅保留验证有效的 2 个 slug |
| Ashby 401 | 需要 auth | 放弃，不抓 |

#### 公司列表维护 (`company_list.py`)

通过 live 探测建立并维护已验证 slug 列表（失效 slug 被 scraper 静默跳过）：
- Greenhouse: 55+ 公司，按 tier 分级（f500 / tier1 / tier2）
- 含 Stripe、Cloudflare、Anthropic、Scale AI、CoreWeave、Samsara 等
- Lever: 2 个（Mistral、Highspot）
- SmartRecruiters: 3 个（Canva、Palantir、Uber）

### 5B — 前端仪表盘（Next.js 14）

**技术选型**: Next.js 14 App Router + Tailwind + SWR + Recharts

#### 页面结构

| 路由 | 功能 |
|------|------|
| `/` | Dashboard — 趋势图 + SSE pipeline 实时流 + 成本卡片 |
| `/jobs` | 职位列表（SWR 轮询） |
| `/applications` | 投递记录 + 状态筛选 |
| `/resume` | 简历上传 → ingest → chunk 可视化 |

#### 关键组件

- `StatsChart` — Recharts AreaChart，LinearGradient 填充，`formatter` 不加类型注解（避免 `ValueType` 兼容问题）
- `PipelineStream` — `fetch` + `ReadableStream` 解析 `data: {...}\n\n` SSE 格式
- `Sidebar` — 4 个 nav item（Dashboard / Jobs / Applications / Resume）

#### 踩坑

| 问题 | 修复 |
|------|------|
| `next.config.ts` not supported（Next 14.2.29）| 改名为 `next.config.mjs` |
| StatsChart TypeScript `formatter` 类型不兼容 | 去掉显式类型注解 |

#### 后端新 API

- `GET /api/stats/daily` — 7 天 job/application 统计 + 估算成本（`COST_PER_JOB = 0.002`）
- `POST /api/agents/stream` — SSE，每个 LangGraph node 完成时推送事件

### 5C — DB 持久化（G）

**目标**: 流水线产出真正写入数据库，Dashboard 数据有来源。

#### `app/db/crud.py`

```python
bulk_upsert_jobs(job_dicts)     # 按 content_hash / source_id 去重，批量插入
upsert_application(...)         # 创建或更新 Application 行
get_or_create_default_user()    # 固定 UUID 000...001，首次自动创建
```

#### 节点更新

**`scraper_node`**（之前只放 state）:
1. 去重后调 `bulk_upsert_jobs(unique)` → 返回 DB UUID 列表
2. 将 `db_id` 写回每个 job dict，供下游节点使用
3. 调 `get_or_create_default_user()` → 写入 `user_id` 到 state

**`tracker_node`**（之前是注释存根）:
1. 从 state 取 `job.db_id` + `user_id`（UUID 字符串）
2. 映射 `pipeline_status` → DB status enum（skip→scraped, notify→matched, tailored→tailored）
3. 调 `upsert_application()` → 返回并记录 application UUID

#### Alembic 设置

- 安装 `alembic>=1.13.0`（uv）
- `alembic init alembic`
- `alembic/env.py` 改写为 async 版本（`async_engine_from_config` + `asyncio.run`）
- 自动导入 `app.db.models` 保证 `Base.metadata` 已注册所有表

### 5D — Extension Analyze Tab（F）+ 公司列表扩展（E）

#### Extension 新增（`v1.1.0`）

**`shared/types.ts`** 新增:
```typescript
interface PageJobInfo  { title, company, jd_text, url }
interface MatchReport  { match_score, summary, strengths, gaps, dimensions }
```

**`content/inject.ts`** 新增消息监听:
```typescript
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'EXTRACT_JD') → 多选择器 JD 提取
  if (msg.type === 'AUTOFILL')  → 表单预填
})
```

JD 提取优先级: Greenhouse `#content` → Lever `.section-content` → LinkedIn `.jobs-description__content` → `article` → `main` → `body.innerText[:8000]`

**`popup/App.tsx`** 重构为 3-tab：

| 标签 | 功能 |
|------|------|
| 任务 | 现有 pending task 列表 |
| 分析 | 提取当前页 JD → `/api/match` → 匹配度环形图 + strengths/gaps → "定制简历" 触发 `/api/agents/run` |
| 设置 | 简历文本输入 + `chrome.storage.local` 持久化 |

**`manifest.json`** v1.1.0:
- 新增 `tabs` permission（`sendMessage` 到 content script 需要）
- 新增 host perms: SmartRecruiters + RemoteOK + WeWorkRemotely

#### 公司列表新增（探测 40+ 候选 slug 后确认 4 个）

| slug | 公司 | 职位数 | tier |
|------|------|--------|------|
| scaleai | Scale AI | 176 | tier1 |
| coreweave | CoreWeave | 272 | tier1 |
| samsara | Samsara | 309 | tier1 |
| cockroachlabs | CockroachDB | 35 | tier2 |

---

## 当前状态快照（2026-06-22）

### 已完成

- **后端**: 8 个 API 路由，5 节点 LangGraph 流水线，7 路 scraper，DB 持久化
- **前端**: 4 页面 Next.js 14 Dashboard，SSE 实时流，Recharts 趋势图
- **Extension**: 3-tab MV3，JD 提取 + 匹配分析 + 表单自动填充
- **测试**: 99 tests passed

### 待完成

| 优先级 | 项目 |
|--------|------|
| 🔴 | Dockerfile + docker-compose 部署 |
| 🔴 | `alembic revision --autogenerate` + `upgrade head` 建初始 migration |
| 🟡 | `daily_scan.py` 循环多 job（当前每次只处理 pipeline 第一个 job）|
| 🟡 | 用户认证（当前硬编码 default user UUID）|
| 🟡 | Extension `icons/` 目录缺 PNG（安装有 warning）|
| 🟢 | Workday/iCIMS ATS 更多公司覆盖 |
| 🟢 | `/api/match` 结果 Redis 缓存（TTL 1h）|
