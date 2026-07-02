import json
import logging
from typing import cast

from app.core.cache import redis_client

logger = logging.getLogger(__name__)

# Maximum number of Q&A pairs (turns) to remember per session to prevent prompt bloat.
MAX_TURNS_PER_SESSION = 5


async def get_session_history(session_id: str | None) -> list[dict[str, str]]:
    """
    Retrieves the chat history for a given session ID.
    Returns an empty list if no session_id is provided or no history exists.
    """
    if not session_id:
        return []

    if redis_client is None:
        logger.warning("Redis Client Not Initialized, Returning Empty History")
        return []

    cached = await redis_client.get(f"session:{session_id}")
    if cached:
        # Reset the TTL on read
        await redis_client.expire(f"session:{session_id}", 86400)
        return cast(list[dict[str, str]], json.loads(cached))

    return []


async def append_session_history(session_id: str | None, question: str, sql: str) -> None:
    """
    Appends a new Q&A turn to the session history.
    Enforces maximum turns per session.
    """
    if not session_id:
        return

    history = await get_session_history(session_id)

    history.append({
        "question": question,
        "sql": sql
    })

    # Cap the history for this session
    if len(history) > MAX_TURNS_PER_SESSION:
        history = history[-MAX_TURNS_PER_SESSION:]

    if redis_client is None:
        logger.warning("Redis Client Not Initialized, Cannot Save History")
        return

    await redis_client.set(f"session:{session_id}", json.dumps(history), ex=86400)
