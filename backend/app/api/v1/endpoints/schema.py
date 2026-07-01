import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.reader import get_cached_schema

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/schema", response_model=None)
async def get_schema() -> dict[str, Any] | JSONResponse:
    try:
        tables = get_cached_schema()
    except RuntimeError:
        logger.warning("Schema Cache Not Loaded")
        return JSONResponse(
            status_code=503,
            content={"detail": "Schema not yet loaded"},
        )
    return {"tables": tables}
