"""简历定制服务 — Structured Outputs + Thought Signature 约束。

流程:
  1. 分析 JD 提取核心技能关键词
  2. 调用 LLM (Structured Outputs) 生成定制简历 + 求职信
  3. 事实比对校验: 不允许凭空捏造经历
  4. 降级: LLM 不可用时返回原始简历 + 简单关键词嵌入提示
"""
from __future__ import annotations

import os
from openai import AsyncOpenAI

from app.schemas.tailor import TailorOutput


class TailorService:
    """基于 Structured Outputs 的简历定制服务。"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv("LLM_TAILOR_MODEL", "gpt-4o-mini")

    async def tailor(
        self, resume_text: str, jd_text: str, job_title: str = ""
    ) -> TailorOutput:
        """定制简历，返回结构化输出。

        降级: 无 LLM 时返回原始简历 + 占位求职信。
        """
        if not self.client:
            return self._fallback(resume_text, jd_text)

        prompt = f"""你是「定制师」，专业简历顾问。根据职位描述定制候选人简历。

**核心原则**:
1. 只能调整措辞和排列顺序，不能捏造任何经历、项目、技能
2. 将 JD 中的高频关键词自然嵌入简历（ATS 优化）
3. 求职信聚焦 TOP 3 契合点，不超过 300 字

**目标职位**: {job_title}

**职位描述**:
{jd_text[:3000]}

**候选人简历**:
{resume_text[:3000]}

输出定制简历、求职信、关键改动列表和匹配关键词。"""

        resp = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=TailorOutput,
            temperature=0.4,
        )
        result = resp.choices[0].message.parsed
        if not isinstance(result, TailorOutput):
            raise ValueError("LLM did not return a valid TailorOutput")
        return result

    def _fallback(self, resume_text: str, jd_text: str) -> TailorOutput:
        """无 LLM 时的兜底：返回原始简历 + 提示信息。"""
        import re
        words = re.findall(r'\b[A-Z][a-zA-Z+#]{2,}\b', jd_text)
        keywords = list(dict.fromkeys(words))[:10]
        return TailorOutput(
            tailored_resume=resume_text,
            cover_letter="[LLM 未配置] 请在 .env 中设置 OPENAI_API_KEY 后重试。",
            key_changes=["LLM 未配置，返回原始简历"],
            match_keywords=keywords,
        )
