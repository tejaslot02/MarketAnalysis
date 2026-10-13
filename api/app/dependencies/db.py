"""Async SQLAlchemy session and engine factory."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import get_settings

_async_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Return singleton AsyncEngine instance."""
    global _async_engine, _session_maker
    if _async_engine is None:
        settings = get_settings()
        # Ensure asyncpg dialect is present
        db_url = settings.database_url
        if "postgresql+psycopg2://" in db_url:
            db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        elif "postgresql://" in db_url and "postgresql+asyncpg://" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

        _async_engine = create_async_engine(
            db_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=settings.db_pool_pre_ping,
            future=True,
        )
        _session_maker = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an AsyncSession."""
    get_async_engine()
    assert _session_maker is not None
    async with _session_maker() as session:
        yield session
