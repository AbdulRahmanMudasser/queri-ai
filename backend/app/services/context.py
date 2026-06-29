import hashlib
import json
import logging
import math
from typing import Any

from app.services.embeddings import EmbeddingsProvider

logger = logging.getLogger(__name__)

# Global caches for schema embeddings
_table_embeddings_cache: dict[str, list[float]] = {}
_schema_hash: str | None = None


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
    global _table_embeddings_cache, _schema_hash

    if not schema:
        return []

    current_hash = _get_schema_hash(schema)
    if _schema_hash != current_hash:
        logger.info("Schema hash changed or cache cold. Generating new table embeddings.")
        _table_embeddings_cache.clear()
        _schema_hash = current_hash

        for table in schema:
            desc = _get_table_description(table)
            emb = await provider.get_embedding(desc)
            _table_embeddings_cache[table["name"]] = emb

    # Generate question embedding
    question_emb = await provider.get_embedding(question)

    # Calculate similarity scores
    scored_tables = []
    for table in schema:
        table_name = table["name"]
        table_emb = _table_embeddings_cache.get(table_name)
        if table_emb is not None:
            try:
                score = cosine_similarity(question_emb, table_emb)
            except ValueError:
                logger.warning("Embedding dimension mismatch in cache. Regenerating embeddings.")
                _table_embeddings_cache.clear()
                # Regenerate all table embeddings
                for t in schema:
                    desc = _get_table_description(t)
                    emb = await provider.get_embedding(desc)
                    _table_embeddings_cache[t["name"]] = emb
                table_emb = _table_embeddings_cache[table_name]
                score = cosine_similarity(question_emb, table_emb)
            scored_tables.append((score, table))

    # Sort scored tables descending by score
    scored_tables.sort(key=lambda x: x[0], reverse=True)

    # Filter tables: threshold >= 0.35, fallback to top-3
    pruned = [table for score, table in scored_tables if score >= 0.35]
    if not pruned:
        logger.info("No tables crossed the 0.35 threshold. Falling back to top-3.")
        pruned = [table for score, table in scored_tables[:3]]

    pruned_names = {t["name"] for t in pruned}
    # Maintain original order of tables
    return [table for table in schema if table["name"] in pruned_names]
