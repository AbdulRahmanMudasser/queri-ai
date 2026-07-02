import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.cache import close_redis, init_redis
from app.core.config import settings
from app.core.logger import setup_logging
from app.db.reader import load_schema
from app.db.seeder import seed_database
from app.db.session import AsyncSessionLocal
from app.services.embeddings import get_embeddings_provider

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    logger.info("Starting Up Queri.ai Backend", extra={"env": settings.ENV})

    # Step 0: Initialize cache
    await init_redis()

    # Step 1: Database tables are managed by Alembic migrations.

    # Step 2: Seed database and load schema
    async with AsyncSessionLocal() as db:
        provider = get_embeddings_provider()
        await seed_database(db, provider)

        tables = await load_schema(db)
        logger.info("Schema Loaded: %d Tables", len(tables))
    yield
    logger.info("Shutting Down Queri.ai Backend")
    await close_redis()


app = FastAPI(
    title="Queri.ai API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
    logger.exception("Unhandled Exception", exc_info=exc)
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
