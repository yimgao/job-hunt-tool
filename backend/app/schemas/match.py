"""Pydantic schema for match API."""
from __future__ import annotations
from pydantic import BaseModel, Field


class MatchDimensions(BaseModel):
    """四个评估维度的评分。"""
    skills_match: float = Field(ge=0, le=1, description="技能匹配度")
    experience_match: float = Field(ge=0, le=1, description="经验匹配度")
    industry_match: float = Field(ge=0, le=1, description="行业匹配度")
    culture_fit: float = Field(ge=0, le=1, description="文化契合度")


class MatchReport(BaseModel):
    """Matcher Agent 的结构化输出。也是 LLM Structured Outputs 的 target schema。"""
    job_id: str = Field(default="", description="关联职位 ID")
    match_score: float = Field(ge=0, le=1, description="总体匹配度 0-1")
    confidence: float = Field(ge=0, le=1, description="模型置信度")
    dimensions: MatchDimensions = Field(description="各维度评分")
    strengths: list[str] = Field(default_factory=list, description="优势列表")
    gaps: list[str] = Field(default_factory=list, description="差距列表")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")
    should_apply: bool = Field(default=False, description="是否建议投递")
    priority: str = Field(default="low", pattern="^(high|medium|low)$", description="优先级")


class MatchRequest(BaseModel):
    """POST /api/match 请求体。"""
    resume_text: str = Field(min_length=50, description="简历全文")
    jd_text: str = Field(min_length=50, description="JD 全文")


class MatchResponse(BaseModel):
    """POST /api/match 响应体。"""
    report: MatchReport
    report_id: str = Field(description="匹配报告 ID")
    llm_model: str = Field(description="使用的模型")
    llm_cost: float = Field(ge=0, description="API 调用成本 ($)")
