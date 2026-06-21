# JobHunt-Flow — 成本控制面板

> 零启动预算下的 API 费用管控策略。

---

## 成本模型

| 环节 | 策略 | 模型 | 调用频次 | 单次成本 | 日成本 |
|------|------|------|----------|----------|--------|
| 职位获取 | RSS / 免费 API | — | 2次/日 | $0.00 | $0.00 |
| 去重 | 本地 TF-IDF | scikit-learn | 100次/日 | $0.00 | $0.00 |
| 向量化 | 开源 Embedding | bge-small / text-embedding-3-small | 50次/日 | $0.00 | $0.00 |
| 初筛 | LLM 初筛 | Gemini 1.5 Flash (free tier) | 100次/日 | $0.00 | $0.00 |
| 深度分析 | LLM 深度 | GPT-4o-mini | 5次/日 | ~$0.02 | ~$0.10 |
| 简历定制 | LLM 定制 | GPT-4o-mini | 3次/日 | ~$0.05 | ~$0.15 |
| **合计** | — | — | — | — | **< $0.30/日** |

---

## LLM 路由策略

```python
LLM_ROUTING = {
    "quick_scan": {             # 80% 流量
        "provider": "gemini",   # Gemini 1.5 Flash (free tier: 60 req/min)
        "model": "gemini-1.5-flash",
        "cost_per_1k": 0.000,
        "max_retry": 1,
        "fallback": "gpt-4o-mini"
    },
    "deep_analyze": {           # 15% 流量
        "provider": "openai",
        "model": "gpt-4o-mini",
        "cost_per_1k": 0.00015,  # input
        "max_retry": 2,
        "fallback": "gpt-4o"
    },
    "tailor": {                 # 5% 流量
        "provider": "openai",
        "model": "gpt-4o-mini",
        "cost_per_1k": 0.00015,
        "max_retry": 2,
        "structured_output": True  # 强制 Function Calling
    }
}
```

---

## 模型降级链

```
Gemini (免费) ─── 触发限流 ──→ GPT-4o-mini ─── 触发配额 ──→ Hermes 自带模型
     ↑                                                           │
     └──────────────────── 次日恢复 ─────────────────────────────┘
```

---

## 预算监控

```sql
-- 每日成本报告
SELECT
    DATE(created_at) AS day,
    agent,
    COUNT(*) AS calls,
    ROUND(SUM(llm_cost)::numeric, 4) AS total_cost
FROM agent_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY day, agent
ORDER BY day DESC;

-- 月度预算告警
SELECT SUM(llm_cost) < 9.00 AS within_budget  -- $9/月 = $0.30/日
FROM agent_logs
WHERE created_at >= DATE_TRUNC('month', NOW());
```

---

## 配置

```yaml
# config.yaml
cost_control:
  monthly_budget: 9.00              # 月上限 $9
  daily_warn_at: 0.25               # 日超 $0.25 告警
  model_routing: enabled            # 自动路由到最经济的模型
  auto_downgrade: true              # 超预算时降级为纯 TF-IDF
  notify_on_overage: true           # 超预算时推送通知
```
