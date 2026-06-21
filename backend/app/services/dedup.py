"""TF-IDF 模糊去重 + Redis 哈希缓存。

两层去重:
  Layer 1 (O(1)): Redis SET — content_hash 精确匹配，跨进程/重启持久
  Layer 2 (O(n)): TF-IDF 余弦相似度 — 近似重复，阈值 95%

RedisHashCache 可选；不可用时自动降级到纯 TF-IDF。
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── Normalization ─────────────────────────────────────────────────────────────


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_content_hash(jd_text: str) -> str:
    return hashlib.sha256(_normalize(jd_text).encode()).hexdigest()


# ── TF-IDF ───────────────────────────────────────────────────────────────────


def is_similar(
    new_text: str,
    existing_texts: Sequence[str],
    threshold: float = 0.95,
) -> bool:
    if not existing_texts:
        return False
    corpus = [_normalize(t) for t in existing_texts]
    query = _normalize(new_text)
    vectorizer = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus + [query])
    except ValueError:
        return False
    query_vec = tfidf_matrix[-1]
    corpus_matrix = tfidf_matrix[:-1]
    similarities = cosine_similarity(query_vec, corpus_matrix).flatten()
    return bool(np.any(similarities >= threshold))


def filter_duplicates(
    new_jobs: list[dict],
    existing_hashes: set[str],
    existing_jd_texts: list[str],
    similarity_threshold: float = 0.95,
) -> tuple[list[dict], list[dict]]:
    unique: list[dict] = []
    duplicates: list[dict] = []
    seen_hashes: set[str] = set(existing_hashes)
    seen_texts: list[str] = list(existing_jd_texts)

    for job in new_jobs:
        jd_text = job.get("jd_text", "")
        content_hash = compute_content_hash(jd_text)

        if content_hash in seen_hashes:
            duplicates.append(job)
            continue

        if is_similar(jd_text, seen_texts, threshold=similarity_threshold):
            duplicates.append(job)
            continue

        seen_hashes.add(content_hash)
        seen_texts.append(jd_text)
        unique.append({**job, "content_hash": content_hash})

    return unique, duplicates


# ── Redis cache (optional, async) ────────────────────────────────────────────

_REDIS_KEY = "jh:content_hashes"
_TTL_SECONDS = 30 * 86400  # 30 days


class RedisHashCache:
    """Redis SET-based content hash cache — O(1) dedup lookup。

    不可用时所有方法静默降级（返回 False / noop）。
    """

    def __init__(self, url: str | None = None):
        self._url = url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self._url, decode_responses=True)
                await self._client.ping()
            except Exception as exc:
                logger.warning("Redis unavailable: %s — hash cache disabled", exc)
                self._client = False
        return self._client if self._client else None

    async def has(self, content_hash: str) -> bool:
        client = await self._get_client()
        if not client:
            return False
        try:
            return bool(await client.sismember(_REDIS_KEY, content_hash))
        except Exception:
            return False

    async def add(self, content_hash: str) -> None:
        client = await self._get_client()
        if not client:
            return
        try:
            await client.sadd(_REDIS_KEY, content_hash)
            await client.expire(_REDIS_KEY, _TTL_SECONDS)
        except Exception as exc:
            logger.debug("Redis add failed: %s", exc)

    async def add_many(self, hashes: list[str]) -> None:
        if not hashes:
            return
        client = await self._get_client()
        if not client:
            return
        try:
            await client.sadd(_REDIS_KEY, *hashes)
            await client.expire(_REDIS_KEY, _TTL_SECONDS)
        except Exception as exc:
            logger.debug("Redis add_many failed: %s", exc)

    async def close(self) -> None:
        if self._client and self._client is not False:
            await self._client.aclose()


# Module-level singleton
redis_cache = RedisHashCache()
