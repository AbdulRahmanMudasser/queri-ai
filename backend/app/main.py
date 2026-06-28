import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logger import setup_logging
from app.db.reader import load_schema
from app.db.session import AsyncSessionLocal

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    logger.info("Starting up Queri.ai backend", extra={"env": settings.ENV})
    async with AsyncSessionLocal() as db:
        try:
            tables = await load_schema(db)
            logger.info("Schema loaded: %d tables", len(tables))
        except Exception:
            logger.warning("Could not load schema at startup — DB may be unavailable")
    yield
    logger.info("Shutting down Queri.ai backend")


app = FastAPI(
    title="Queri.ai API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
