# JobHunt-Flow — Multi-Agent 详细设计

> 每个智能体的职责、接口、Prompt、降级策略。

---

## 1. Scraper Agent — 猎犬

**文件**: `backend/app/services/scraper.py` + `backend/app/agents/scraper_node.py`

### 三重降级策略

| 优先级 | 方案 | 适用平台 | 风险 | 频率 |
|--------|------|----------|------|------|
| 🥇 **Tier 1** | 聚合 API / RSS 订阅 | LinkedIn RSS, Google Jobs API, 公开职位聚合 | 零 | 每日 2 次 |
| 🥈 **Tier 2** | 动态代理池 + HTTP 接口逆向 | BOSS直聘 REST API 逆向 | 中 | 每日 1 次 |
| 🥉 **Tier 3** | undetected-chromedriver + 随机指纹 | 全平台兜底 | 高 | 每日 1 次，凌晨 |

### 去重策略

**文件**: `backend/app/services/dedup.py`

```python
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def compute_content_hash(jd_text: str) -> str:
    """TF-IDF 清洗后生成哈希，用于模糊去重"""
    cleaned = re.sub(r'\s+', ' ', jd_text.lower().strip())
    # 移除薪资数字、日期等易变信息
    cleaned = re.sub(r'\d{4}-\d{2}-\d{2}', '', cleaned)
    cleaned = re.sub(r'\d{2,}k?', '', cleaned)
    # TF-IDF + cosine similarity 判定
    # 相似度 > 0.95 → 判定为重复
    pass

def is_duplicate(new_jd: str, existing_hashes: list[str]) -> bool:
    """与已有职位做模糊去重"""
    vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    corpus = [new_jd] + existing_hashes  # 实际需要存储原始文本
    tfidf = vectorizer.fit_transform(corpus)
    sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    return any(s > 0.95 for s in sims)
```

### 输出 Schema

```python
class ScraperOutput(BaseModel):
    new_jobs: list[dict]       # 新职位列表
    duplicates_skipped: int    # 去重丢弃数
    sources_summary: dict      # 各平台采集统计
```

---

## 2. Matcher Agent — 鉴宝师

**文件**: `backend/app/services/matcher.py` + `backend/app/agents/matcher_node.py`

### RAG 召回流程

```python
async def match_job(jd_text: str, user_id: str) -> MatchReport:
    # 1. 提取 JD 技能
    skills = extract_skills(jd_text)  # 本地 regex

    # 2. 召回简历 chunk
    chunks = await vector_store.search(
        user_id=user_id,
        query=jd_text,          # 直接用 JD 做 embedding query
        top_k=5,
        threshold=0.6
    )

    # 3. 初筛 (低成本模型)
    preliminary = await quick_scan(chunks, jd_text)
    if preliminary.match_score < 0.5:
        return preliminary  # 不浪费高成本模型

    # 4. 深度分析 (高成本模型 + Structured Outputs)
    deep = await deep_analyze(chunks, jd_text)
    return deep
```

### LLM Prompt (Matcher 初筛)

```
你是一个招聘匹配助手。根据候选人的经历片段，快速判断是否适合该职位。

候选人经历片段:
{chunks}

职位描述:
{jd_text}

只输出 JSON:
{{"match_score": 0.0-1.0, "confidence": 0.0-1.0, "reason": "一句话理由"}}
```

### LLM Prompt (Matcher 深度分析)

```
你叫「鉴宝师」，资深招聘顾问。你需要输出一份详细的匹配报告。

候选人的相关经历 (RAG 召回):
{chunks}

职位描述:
{jd_text}

请按以下要求评估:
1. 技能匹配 — 硬技能重合度
2. 经验匹配 — 行业/岗位年限匹配度
3. 项目匹配 — 项目复杂度、规模、技术栈一致性
4. 潜力匹配 — 学习能力、转型可行性

严格按 JSON Schema 输出:
{match_report_schema}
```

---

## 3. Tailor Agent — 裁缝

**文件**: `backend/app/services/tailor.py` + `backend/app/agents/tailor_node.py`

### 核心约束

1. **Structured Outputs 强制** — Pydantic BaseModel 驱动，禁止自由文本
2. **Thought Signature** — 模型必须先做事实比对，再出修改方案
3. **差分输出** — 只输出「修改的段落」而非整份简历，减少幻觉空间

### LLM Prompt

```
你叫「裁缝」，简历优化专家。你的任务是针对特定 JD 调整候选人简历措辞。

## 铁律 (必须遵守)
1. 不编造任何经历。如果候选人没有某项经验，跳过，不补充。
2. 不修改时间线、公司名、职位头衔。
3. 只对与 JD 相关的经历做措辞优化：量化成果、突出技术栈。

## 思考步骤 (必须按顺序执行)
<thought_process>
步骤1: 列出 JD 要求的每一项技能/经验
步骤2: 在简历原文中找到对应证据 (找不到标注 无)
步骤3: 仅对找到证据的条目做措辞优化
步骤4: 确认没有新增任何不存在的经历
</thought_process>

## 简历原文
{resume_text}

## JD 全文
{jd_text}

请按以下 JSON Schema 输出修改方案:
{tailor_schema}
```

### 求职信模板

```python
COVER_LETTER_TEMPLATE = """尊敬的{招聘经理}：

我在{平台}上看到了贵公司{职位}的招聘信息，很感兴趣。

我目前在{当前公司}担任{当前职位}，有{X}年{领域}经验。
{与JD最相关的1-2个项目经历，200字内}

我对贵公司的{业务/产品}特别感兴趣，因为{理由}。
希望能有机会进一步交流。

附件是我的简历，期待您的回复。

{姓名}
{联系方式}"""
```

---

## 4. Applicant Agent — 投递手

**文件**: `backend/app/agents/applicant_node.py`

### 执行逻辑

```python
async def prepare_application(application_id: str) -> dict:
    # 1. 从 DB 读取投递任务
    app = await get_application(application_id)

    # 2. 生成定制简历 PDF (或缓存)
    pdf_url = await generate_pdf(app.tailored_resume)

    # 3. 创建 Extension 任务
    task = await create_extension_task(
        application_id=app.id,
        prefill_data={
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "resume_url": pdf_url,
            "cover_letter": app.tailored_cover_letter
        }
    )

    # 4. 推送到用户浏览器
    await notify_extension(user.id, task.id)

    return {"task_id": task.id, "expires_in": 3600}
```

### Chrome Extension 通信

```typescript
// extension/content/inject.ts
interface ExtensionTask {
  task_id: string;
  prefill_data: {
    name: string;
    email: string;
    phone: string;
    resume_url: string;
    cover_letter: string;
  };
}

// 检测到投递表单页面 → 注入浮窗
const task = await fetch(`${API}/api/ext/task/${taskId}`);
showFloatingPanel(task.prefill_data);

// 用户点击确认 → 自动填入，留空 Submit
document.querySelector<HTMLInputElement>('[name="name"]')!.value = task.prefill_data.name;
document.querySelector<HTMLInputElement>('[name="email"]')!.value = task.prefill_data.email;
// ... 用户手动点击 Submit
```

---

## 5. Tracker Agent — 记账先生

**文件**: `backend/app/agents/tracker_node.py`

### 漏斗 SQL

```sql
SELECT
    COUNT(*) AS total_found,
    SUM(CASE WHEN status >= 'matched' THEN 1 ELSE 0 END) AS matched,
    SUM(CASE WHEN status >= 'tailored' THEN 1 ELSE 0 END) AS tailored,
    SUM(CASE WHEN status >= 'applied' THEN 1 ELSE 0 END) AS applied,
    SUM(CASE WHEN status = 'interview' THEN 1 ELSE 0 END) AS interview,
    SUM(CASE WHEN status = 'offer' THEN 1 ELSE 0 END) AS offer,
    ROUND(AVG(match_score), 2) AS avg_match_score
FROM applications
WHERE user_id = $1
  AND created_at >= NOW() - INTERVAL '30 days';
```

### 看板数据输出

```json
{
  "funnel": {
    "found": 150,
    "matched": 90,
    "tailored": 45,
    "applied": 30,
    "interview": 8,
    "offer": 2
  },
  "rates": {
    "match_rate": "60%",
    "apply_rate": "20%",
    "interview_rate": "27%",
    "offer_rate": "7%"
  },
  "best_source": "BOSS直聘",
  "avg_response_days": 3.2,
  "weekly_trend": [
    {"week": "W24", "applied": 5, "interview": 1},
    {"week": "W25", "applied": 8, "interview": 2},
    {"week": "W26", "applied": 12, "interview": 3}
  ]
}
```

---

## 6. Orchestrator Agent — 大脑

**文件**: `backend/app/agents/orchestrator.py`

### 状态机定义 (LangGraph)

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

class AgentState(TypedDict):
    jobs_to_process: list[str]       # 待处理队列
    current_job: str | None
    status: Literal["init","scraping","matching","tailoring",
                    "applying","error","rollback"]
    errors: list[dict]
    pending_approval: list[str]
    metrics: dict

workflow = StateGraph(AgentState)

# 节点注册
workflow.add_node("scraper", scraper_node)
workflow.add_node("matcher", matcher_node)
workflow.add_node("tailor", tailor_node)
workflow.add_node("applicant", applicant_node)
workflow.add_node("tracker", tracker_node)

# 条件边
workflow.add_conditional_edges(
    "matcher",
    lambda state: decide_next(state),
    {"tailor": "tailor", "notify": "notify", "skip": "tracker"}
)

workflow.add_conditional_edges(
    "tailor",
    lambda state: decide_apply(state),
    {"apply": "applicant", "pending": "tracker"}
)

workflow.set_entry_point("scraper")
workflow.add_edge("applicant", "tracker")
workflow.add_edge("tracker", END)
```

### 路由决策函数

```python
def decide_next(state: AgentState) -> str:
    """根据匹配评分路由"""
    score = get_match_score(state["current_job"])
    if score >= 0.6:
        return "tailor"      # 自动进入定制
    elif score >= 0.3:
        return "notify"      # 推送给用户
    else:
        return "skip"         # 跳过

def decide_apply(state: AgentState) -> str:
    """根据用户配置决定自动投递还是等待确认"""
    config = get_user_config()
    if config["auto_apply"]:
        return "apply"
    return "pending"
```

---

## 7. 降级策略矩阵

| 故障场景 | 检测 | 降级动作 | 用户可见 |
|----------|------|----------|----------|
| LLM API 超时 | > 30s 无响应 | 跳过该职位，放入重试队列（最多 3 次） | 否 |
| LLM JSON 解析失败 | Pydantic validation error | 重试 1 次；再失败则回退 TF-IDF 匹配 | Dashboard 标黄 |
| Scraper Tier 1 全挂 | 0 新结果 | 自动升级到 Tier 2 | 否 |
| Scraper Tier 3 被封 | 连续 3 次 403 | 暂停爬取 24h，通知用户 | 通知 |
| Chrome Extension 离线 | Extension 7 天未连接 | 投递任务堆积，下次上线批量推送 | 通知 |
| 数据库连接失败 | SQLAlchemy timeout | 启用内存缓存，后台自动重连 | Dashboard 降级为静态页 |
