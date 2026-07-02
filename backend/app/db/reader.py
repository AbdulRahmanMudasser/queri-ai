import json
import logging
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import redis_client

logger = logging.getLogger(__name__)


async def load_schema(db: AsyncSession) -> list[dict[str, Any]]:
    rows = await _fetch_schema(db)
    tables = await _populate_cache(rows)
    logger.info("Schema Cache Populated With %d Tables", len(tables))
    return rows


async def get_cached_schema() -> list[dict[str, Any]]:
    if redis_client is None:
        raise RuntimeError("Redis client not initialized")
    cached = await redis_client.get("db_schema")
    if not cached:
        raise RuntimeError("Schema cache not loaded")
    return cast(list[dict[str, Any]], json.loads(cached))


async def _populate_cache(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tables: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        table_name = row["table_name"]
        column_info = {"name": row["column_name"], "type": row["data_type"]}
        tables.setdefault(table_name, []).append(column_info)

    result = [{"name": table_name, "columns": columns} for table_name, columns in tables.items()]
    if redis_client:
        await redis_client.set("db_schema", json.dumps(result))
    return result


async def _fetch_schema(db: AsyncSession) -> list[dict[str, Any]]:
    query = text("""
        SELECT
            t.table_name,
            c.column_name,
            c.data_type
        FROM information_schema.tables t
        JOIN information_schema.columns c
            ON t.table_name = c.table_name
            AND t.table_schema = c.table_schema
        WHERE t.table_schema = 'public'
          AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_name, c.ordinal_position
    """)
    result = await db.execute(query)
    rows = result.mappings().all()
    return [dict(r) for r in rows]
