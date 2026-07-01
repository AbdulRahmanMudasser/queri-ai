import os
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
os.environ["GEMINI_API_KEY"] = "test-key"

from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def mock_engine_begin() -> Generator[MagicMock, None, None]:
    with patch("app.db.session.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_engine


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db_session() -> Generator[AsyncMock, None, None]:
    with patch("app.db.session.AsyncSessionLocal") as mock_sessionmaker:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result
        mock_transaction = AsyncMock()
        mock_session.begin = MagicMock(return_value=mock_transaction)
        mock_sessionmaker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sessionmaker.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_session


@pytest.fixture(autouse=True)
def mock_embeddings_provider() -> Generator[MagicMock, None, None]:
    from app.services.embeddings import EmbeddingsProvider

    class DummyEmbeddingsProvider(EmbeddingsProvider):
        async def get_embedding(self, text: str) -> list[float]:
            import hashlib

            h = hashlib.md5(text.encode("utf-8")).digest()
            # Return 384 floats (all-MiniLM size)
            return [float(b) / 255.0 for b in h] * 24

    mock_provider = DummyEmbeddingsProvider()
    target_path = "app.api.v1.endpoints.query.get_embeddings_provider"
    with patch(target_path, return_value=mock_provider) as p:
        yield p
