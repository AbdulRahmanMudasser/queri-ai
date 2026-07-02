from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global redis client
redis_client: redis.Redis[Any] | None = None


async def init_redis() -> None:
    global redis_client
    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        await redis_client.ping()
        logger.info("Connected To Redis At %s", settings.REDIS_URL)
    except Exception as e:
        logger.error("Failed To Connect To Redis: %s", e)
        raise


async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.aclose()  # type: ignore[attr-defined]
        logger.info("Closed Redis Connection")
