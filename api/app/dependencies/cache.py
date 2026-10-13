"""Dragonfly / Redis dependency injection client."""
from __future__ import annotations

import redis

from config.settings import get_settings


def get_redis_client() -> redis.Redis:
    """Return configured Dragonfly Redis client."""
    settings = get_settings()
    return redis.Redis.from_url(settings.dragonfly_url, decode_responses=True)
