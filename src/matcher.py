"""JD-Resume 匹配器 — TF-IDF 相似度 + 技能差距分析。"""

from __future__ import annotations

import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer

# 常见技术关键词词库
SKILL_KEYWORDS = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "ruby",
    "react", "vue", "angular", "next.js", "node.js", "express",
    "fastapi", "django", "flask", "spring", "gin",
    "sql", "nosql", "postgresql", "mysql", "mongodb", "redis",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
    "graphql", "rest", "grpc", "kafka", "rabbitmq",
    "machine learning", "deep learning", "nlp", "llm", "rag",
    "pytorch", "tensorflow", "scikit-learn", "pandas",
    "ci/cd", "git", "linux", "agile", "scrum",
}


def extract_keywords(text: str) -> set[str]:
    """从文本中提取技能关键词（单词边界匹配）。"""
    text_lower = text.lower()
    found = set()
    for kw in SKILL_KEYWORDS:
        if re.search(rf'\b{re.escape(kw)}\b', text_lower):
            found.add(kw)
    return found


def compute_similarity(resume_text: str, jd_text: str) -> float:
    """计算简历与 JD 的 TF-IDF 余弦相似度。"""
    corpus = [resume_text, jd_text]
    vect = TfidfVectorizer(stop_words="english", max_features=500)
    tfidf = vect.fit_transform(corpus)
    similarity = (tfidf * tfidf.T).toarray()[0, 1]
    return similarity


def analyze_gaps(resume_text: str, jd_text: str) -> dict[str, Any]:
    """完整匹配分析：相似度 + 技能差距。"""
    score = compute_similarity(resume_text, jd_text)
    resume_skills = extract_keywords(resume_text)
    jd_skills = extract_keywords(jd_text)

    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills
    extra = resume_skills - jd_skills

    return {
        "match_score": round(score, 4),
        "match_percent": f"{score:.1%}",
        "jd_skill_count": len(jd_skills),
        "resume_skill_count": len(resume_skills),
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "extra_skills": sorted(extra),
        "match_quality": (
            "high" if score > 0.5
            else "medium" if score > 0.3
            else "low"
        ),
    }


def generate_suggestions(result: dict[str, Any]) -> list[str]:
    """根据分析结果生成调整建议。"""
    suggestions = []
    if result["missing_skills"]:
        skills = result["missing_skills"][:5]
        suggestions.append(
            f"🔴 缺失关键技能: {', '.join(skills)}"
            f" — 建议在简历中补充相关经验"
        )
    if result["match_score"] < 0.3:
        suggestions.append(
            "⚠️ 匹配度偏低，建议根据 JD 关键词大幅调整简历"
        )
    elif result["match_score"] < 0.5:
        suggestions.append(
            "📝 匹配度中等，建议强化 JD 中高频出现的技术栈描述"
        )
    if result["extra_skills"]:
        skills = result["extra_skills"][:3]
        suggestions.append(
            f"💡 简历中有 JD 未提及的技能: {', '.join(skills)}"
            f" — 如果相关可保留，否则考虑精简腾出空间"
        )
    return suggestions
