import os
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
os.environ["GEMINI_API_KEY"] = "test-key"

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db_session() -> Generator[AsyncMock, None, None]:
    with patch("app.db.session.AsyncSessionLocal") as mock_sessionmaker:
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin = MagicMock(return_value=mock_transaction)
        mock_sessionmaker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_sessionmaker.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_session
