"""Daily cron script — triggers the full agent pipeline and reports results.

Usage:
    python scripts/daily_scan.py --resume-file /path/to/resume.txt
    python scripts/daily_scan.py --resume-text "Alice Smith, Software Engineer..."

Schedule (crontab example):
    0 8 * * * cd /app && uv run python scripts/daily_scan.py --resume-file /data/resume.txt
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
TIMEOUT = 120.0  # seconds — pipeline can be slow with retries


async def run_pipeline(resume_text: str) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
        resp = await client.post("/api/agents/run", json={"resume_text": resume_text})
        resp.raise_for_status()
        return resp.json()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Daily job-hunt pipeline scan")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--resume-file", type=Path, help="Path to plain-text resume")
    group.add_argument("--resume-text", type=str, help="Resume text inline")
    args = parser.parse_args()

    if args.resume_file:
        resume_text = args.resume_file.read_text(encoding="utf-8")
    else:
        resume_text = args.resume_text

    if len(resume_text.strip()) < 100:
        print("[daily_scan] ERROR: resume text too short (min 100 chars)", file=sys.stderr)
        return 1

    print(f"[daily_scan] Calling {API_BASE}/api/agents/run …")
    try:
        result = await run_pipeline(resume_text)
    except httpx.HTTPStatusError as exc:
        print(f"[daily_scan] HTTP {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        return 1
    except httpx.RequestError as exc:
        print(f"[daily_scan] Connection error: {exc}", file=sys.stderr)
        return 1

    print("[daily_scan] Pipeline result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    status = result.get("pipeline_status", "unknown")
    print(f"\n[daily_scan] Final status: {status}")
    if result.get("errors"):
        print(f"[daily_scan] Errors: {result['errors']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
