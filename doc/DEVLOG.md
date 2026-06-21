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

## 技术债 & 后续

- [ ] `/api/jobs` scraper 接入真实 LinkedIn / Indeed / Boss 直聘
- [ ] `GET /api/match` 结果缓存（Redis TTL 1h，相同 resume+JD hash 命中）
- [ ] Extension 支持多 Tab 并发填表
- [ ] Prometheus metrics + Grafana 监控 LLM 成本曲线
- [ ] 生产 CORS 收紧到具体域名
- [ ] 集成测试（Docker Compose 起 postgres/redis，跑端到端 pipeline）
