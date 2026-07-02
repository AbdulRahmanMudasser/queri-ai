from unittest.mock import AsyncMock, patch

import pytest

from app.services.history import (
    MAX_TURNS_PER_SESSION,
    append_session_history,
    get_session_history,
)


@pytest.fixture
def mock_redis():
    with patch("app.services.history.redis_client", new_callable=AsyncMock) as mock:
        store = {}

        async def mock_get(key):
            return store.get(key)

        async def mock_set(key, value, ex=None):
            store[key] = value

        async def mock_expire(key, time):
            pass

        mock.get.side_effect = mock_get
        mock.set.side_effect = mock_set
        mock.expire.side_effect = mock_expire
        yield mock


@pytest.mark.anyio
async def test_append_and_get_history(mock_redis) -> None:
    session_id = "test-session-1"

    assert await get_session_history(session_id) == []

    await append_session_history(session_id, "Hello?", "SELECT 1")
    history = await get_session_history(session_id)

    assert len(history) == 1
    assert history[0]["question"] == "Hello?"
    assert history[0]["sql"] == "SELECT 1"


@pytest.mark.anyio
async def test_history_turn_capping(mock_redis) -> None:
    session_id = "test-session-2"

    for i in range(MAX_TURNS_PER_SESSION + 3):
        await append_session_history(session_id, f"Q{i}", f"SQL{i}")

    history = await get_session_history(session_id)

    assert len(history) == MAX_TURNS_PER_SESSION
    assert history[-1]["question"] == f"Q{MAX_TURNS_PER_SESSION + 2}"


@pytest.mark.anyio
async def test_history_none_session(mock_redis) -> None:
    await append_session_history(None, "Q", "SQL")
    assert await get_session_history(None) == []
    assert mock_redis.set.call_count == 0
