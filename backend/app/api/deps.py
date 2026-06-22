"""FastAPI shared dependencies."""
from __future__ import annotations

import os

from fastapi import Header, HTTPException, status

_API_KEY = os.getenv("API_KEY", "")


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    """Enforce API_KEY header when API_KEY env var is set.

    When API_KEY is empty (default dev setup) every request passes through.
    Set API_KEY in .env / docker-compose to lock down the API.
    """
    if _API_KEY and x_api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Api-Key header",
        )
