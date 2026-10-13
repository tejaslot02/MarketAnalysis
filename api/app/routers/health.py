"""Health check router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.app.dependencies.db import get_async_engine

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health(response: Response) -> dict[str, Any]:
    """Liveness check and database connectivity probe."""
    engine = get_async_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = 503
        return {"status": "degraded", "database": "unavailable"}
    return {"status": "ok", "database": "ok"}
