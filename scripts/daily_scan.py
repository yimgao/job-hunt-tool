"""Daily cron script — triggers the full agent pipeline and reports results.

Usage:
    python scripts/daily_scan.py --resume-file /path/to/resume.txt
    python scripts/daily_scan.py --resume-text "Alice Smith, Software Engineer..."
    python scripts/daily_scan.py --resume-file resume.txt --max-jobs 10

Schedule (crontab example):
    0 8 * * * cd /app && uv run python scripts/daily_scan.py --resume-file /data/resume.txt --max-jobs 10
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8001")
API_KEY = os.getenv("API_KEY", "")
TIMEOUT = 300.0


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["X-Api-Key"] = API_KEY
    return h


async def run_single(resume_text: str) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
        resp = await client.post("/api/agents/run", json={"resume_text": resume_text}, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def run_batch(resume_text: str, max_jobs: int, min_score: float) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
        resp = await client.post(
            "/api/agents/batch",
            json={"resume_text": resume_text, "max_jobs": max_jobs, "min_score": min_score},
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Daily job-hunt pipeline scan")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--resume-file", type=Path, help="Path to plain-text resume")
    group.add_argument("--resume-text", type=str, help="Resume text inline")
    parser.add_argument("--max-jobs", type=int, default=1,
                        help="Jobs to match/tailor per run (1 = single, >1 = batch endpoint)")
    parser.add_argument("--min-score", type=float, default=0.3,
                        help="Minimum match score to trigger tailoring (batch mode only)")
    args = parser.parse_args()

    if args.resume_file:
        resume_text = args.resume_file.read_text(encoding="utf-8")
    else:
        resume_text = args.resume_text

    if len(resume_text.strip()) < 100:
        print("[daily_scan] ERROR: resume text too short (min 100 chars)", file=sys.stderr)
        return 1

    try:
        if args.max_jobs <= 1:
            print(f"[daily_scan] Single run → {API_BASE}/api/agents/run")
            result = await run_single(resume_text)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if result.get("errors"):
                print(f"[daily_scan] Errors: {result['errors']}", file=sys.stderr)
                return 1
        else:
            print(f"[daily_scan] Batch ({args.max_jobs} jobs) → {API_BASE}/api/agents/batch")
            result = await run_batch(resume_text, args.max_jobs, args.min_score)
            print(f"Scraped: {result['jobs_scraped']}  Processed: {result['jobs_processed']}\n")
            for r in result.get("results", []):
                score = f"{r['match_score']:.0%}" if r.get("match_score") is not None else "  n/a"
                print(f"  [{score:>5}] {r['title'][:50]:<50} @ {r['company'][:25]:<25} → {r['status']}")
            if result.get("errors"):
                print(f"\n[daily_scan] Errors: {result['errors']}", file=sys.stderr)
    except httpx.HTTPStatusError as exc:
        print(f"[daily_scan] HTTP {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        return 1
    except httpx.RequestError as exc:
        print(f"[daily_scan] Connection error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
