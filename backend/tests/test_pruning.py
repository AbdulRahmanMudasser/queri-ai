from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.context import cosine_similarity, prune_schema
from app.services.embeddings import EmbeddingsProvider

MOCK_SCHEMA = [
    {
        "name": "hotels",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "character varying"},
        ],
    },
    {
        "name": "bookings",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "hotel_id", "type": "integer"},
            {"name": "user_id", "type": "integer"},
        ],
    },
    {
        "name": "users",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "email", "type": "character varying"},
        ],
    },
]


@pytest.fixture
def mock_redis():
    with patch("app.services.context.redis_client", new_callable=AsyncMock) as mock:
        store = {}

        async def mock_get(key):
            return store.get(key)

        async def mock_set(key, value, ex=None):
            store[key] = value

        mock.get.side_effect = mock_get
        mock.set.side_effect = mock_set
        yield mock


def test_cosine_similarity_edge_cases() -> None:
    # Exact match
    assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-6
    # Orthogonal
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0]) - 0.0) < 1e-6
    # Opposite
    assert abs(cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-6
    # Zero magnitude vector
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    # Dimension mismatch
    with pytest.raises(ValueError, match="lengths do not match"):
        cosine_similarity([1.0], [1.0, 2.0])


@pytest.mark.asyncio
async def test_prune_schema_threshold(mock_redis) -> None:
    class FixedEmbeddingsProvider(EmbeddingsProvider):
        async def get_embedding(self, text: str) -> list[float]:
            # Use exact prefix matching to avoid substring matching conflicts
            if text.startswith("Table name: hotels"):
                return [1.0, 0.0, 0.0]
            elif text.startswith("Table name: bookings"):
                return [0.0, 1.0, 0.0]
            elif text.startswith("Table name: users"):
                return [0.0, 0.0, 1.0]
            elif "hotels question" in text:
                # Close to hotels (0.9), moderately close to bookings (0.4),
                # orthogonal to users (0.0)
                return [0.9, 0.4, 0.0]
            return [0.0, 0.0, 0.0]

    provider = FixedEmbeddingsProvider()

    pruned = await prune_schema("hotels question", MOCK_SCHEMA, provider)
    pruned_names = [t["name"] for t in pruned]
    assert "hotels" in pruned_names
    assert "bookings" in pruned_names
    assert "users" not in pruned_names


@pytest.mark.asyncio
async def test_prune_schema_fallback(mock_redis) -> None:
    class FixedEmbeddingsProvider(EmbeddingsProvider):
        async def get_embedding(self, text: str) -> list[float]:
            # Use exact prefix matching
            if text.startswith("Table name: hotels"):
                return [1.0, 0.0, 0.0, 0.0]
            elif text.startswith("Table name: bookings"):
                return [0.0, 1.0, 0.0, 0.0]
            elif text.startswith("Table name: users"):
                return [0.0, 0.0, 1.0, 0.0]
            elif "unrelated question" in text:
                # All low similarities (e.g. 0.1, 0.2, 0.15)
                # Normalize vector to magnitude 1.0
                return [0.1, 0.2, 0.15, 0.95]
            return [0.0, 0.0, 0.0, 0.0]

    provider = FixedEmbeddingsProvider()

    # All table similarity scores are below 0.35 threshold
    # Fallback should return all 3 tables (top-3 fallback)
    pruned = await prune_schema("unrelated question", MOCK_SCHEMA, provider)
    assert len(pruned) == 3
    assert {t["name"] for t in pruned} == {"hotels", "bookings", "users"}


@patch("app.api.v1.endpoints.query.get_cached_schema", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.query.translate")
def test_generate_endpoint_pruning_integration(
    mock_translate: MagicMock,
    mock_get_cached_schema: AsyncMock,
    client: TestClient,
    mock_db_session: AsyncMock,
    mock_redis,
) -> None:
    _ = mock_db_session

    mock_get_cached_schema.return_value = MOCK_SCHEMA
    mock_translate.return_value = {
        "sql": "SELECT name FROM hotels",
        "reasoning": "Standard hotels query",
        "tables_used": ["hotels"],
    }

    response = client.post(
        "/api/v1/query/generate",
        json={"question": "show me hotels in Lahore"},
    )
    assert response.status_code == 200
    sql_result = response.json()["sql"]
    assert "SELECT" in sql_result
    assert "name" in sql_result
    assert "hotels" in sql_result
    assert mock_translate.call_count == 1

    args, _ = mock_translate.call_args
    pruned_schema_passed = args[1]
    assert isinstance(pruned_schema_passed, list)
