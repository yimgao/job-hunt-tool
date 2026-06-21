"""Pydantic schema for TailorAgent Structured Output."""
from __future__ import annotations
from pydantic import BaseModel, Field


class TailorOutput(BaseModel):
    """TailorAgent 的结构化输出 — LLM Structured Outputs target schema。"""
    tailored_resume: str = Field(description="定制化简历全文，针对该职位优化")
    cover_letter: str = Field(description="求职信，突出与岗位的契合点")
    key_changes: list[str] = Field(description="简历改动摘要，每条描述一项具体变更")
    match_keywords: list[str] = Field(description="从 JD 中提取并嵌入简历的关键词")
