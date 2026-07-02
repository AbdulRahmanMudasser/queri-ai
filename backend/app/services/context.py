import asyncio
import hashlib
import json
import logging
import math
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import redis_client
from app.core.config import settings
from app.services.embeddings import EmbeddingsProvider

logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if len(v1) != len(v2):
        raise ValueError(f"Vector lengths do not match: {len(v1)} != {len(v2)}")
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=True))
    magnitude_v1 = math.sqrt(sum(a * a for a in v1))
    magnitude_v2 = math.sqrt(sum(b * b for b in v2))
    if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
        return 0.0
    return dot_product / (magnitude_v1 * magnitude_v2)


def _get_schema_hash(schema: list[dict[str, Any]]) -> str:
    serialized = json.dumps(schema, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _get_table_description(table: dict[str, Any]) -> str:
    cols_str = ", ".join(f"{col['name']} ({col['type']})" for col in table["columns"])
    return f"Table name: {table['name']}. Columns: {cols_str}."


async def prune_schema(
    question: str,
    schema: list[dict[str, Any]],
    provider: EmbeddingsProvider,
) -> list[dict[str, Any]]:

    if not schema:
        return []

    # Generate question embedding
    question_emb = await provider.get_embedding(question)

    # Calculate similarity scores
    scored_tables = []
    for table in schema:
        table_name = table["name"]

        # calculate table hash based only on this table's structure
        table_serialized = json.dumps(table, sort_keys=True)
        table_hash = hashlib.sha256(table_serialized.encode("utf-8")).hexdigest()

        if redis_client is None:
            raise RuntimeError("Redis client not initialized")

        cache_data = await redis_client.get(f"table_emb:{table_name}")
        cache_entry = json.loads(cache_data) if cache_data else None

        if cache_entry is None or cache_entry.get("hash") != table_hash:
            logger.info(
                "Table %s Hash Changed Or Cache Cold. Generating New Embedding.", table_name
            )
            desc = _get_table_description(table)
            emb = await provider.get_embedding(desc)
            cache_entry = {"hash": table_hash, "embedding": emb}
            await redis_client.set(f"table_emb:{table_name}", json.dumps(cache_entry))
            table_emb = emb
        else:
            table_emb = cache_entry["embedding"]

        try:
            score = await asyncio.to_thread(cosine_similarity, question_emb, table_emb)
        except ValueError:
            logger.warning(
                "Embedding Dimension Mismatch In Cache. Regenerating Embedding for %s.", table_name
            )
            desc = _get_table_description(table)
            emb = await provider.get_embedding(desc)
            cache_entry = {"hash": table_hash, "embedding": emb}
            await redis_client.set(f"table_emb:{table_name}", json.dumps(cache_entry))
            table_emb = emb
            score = await asyncio.to_thread(cosine_similarity, question_emb, table_emb)

        scored_tables.append((score, table))

    # Sort scored tables descending by score
    scored_tables.sort(key=lambda x: x[0], reverse=True)

    # Filter tables: threshold >= settings.SIMILARITY_THRESHOLD, fallback to top-3
    pruned = [table for score, table in scored_tables if score >= settings.SIMILARITY_THRESHOLD]
    if not pruned:
        logger.info(f"No Tables Crossed The {settings.SIMILARITY_THRESHOLD} Threshold. Falling Back To Top-3.")
        pruned = [table for score, table in scored_tables[:3]]

    pruned_names = {t["name"] for t in pruned}
    # Maintain original order of tables
    return [table for table in schema if table["name"] in pruned_names]


async def get_few_shot_examples(
    question: str,
    db: AsyncSession,
    provider: EmbeddingsProvider,
    top_k: int = 2,
) -> list[dict[str, str]]:
    from sqlalchemy import select

    from app.db.models import FewShotExample

    question_emb = await provider.get_embedding(question)

    result = await db.execute(
        select(FewShotExample)
        .order_by(FewShotExample.question_vector.cosine_distance(question_emb))
        .limit(top_k)
    )
    rows = result.scalars().all()

    return [{"question": r.question, "sql": r.sql_query} for r in rows]


async def get_business_rules(db: AsyncSession) -> list[str]:
    if redis_client is None:
        raise RuntimeError("Redis client not initialized")

    cached = await redis_client.get("business_rules")
    if cached:
        return cast(list[str], json.loads(cached))

    from sqlalchemy import select

    from app.db.models import BusinessRule

    result = await db.execute(select(BusinessRule))
    rows = result.scalars().all()
    rules = [row.rule_value for row in rows]

    await redis_client.set("business_rules", json.dumps(rules), ex=3600)
    return rules
