import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logger import setup_logging
from app.db.models import Base
from app.db.reader import load_schema
from app.db.seeder import seed_database
from app.db.session import AsyncSessionLocal, engine
from app.services.embeddings import get_embeddings_provider

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    logger.info("Starting Up Queri.ai Backend", extra={"env": settings.ENV})

    # Step 1: Create ORM tables (idempotent — CREATE TABLE IF NOT EXISTS)
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database Tables Verified/Created.")
    except Exception:
        logger.warning(
            "Could not Create Database Tables At Startup — DB May Be Unavailable", exc_info=True
        )

    # Step 2: Seed database and load schema
    async with AsyncSessionLocal() as db:
        try:
            provider = get_embeddings_provider()
            await seed_database(db, provider)
        except Exception:
            logger.warning("Database Seeding Failed At Startup", exc_info=True)

        try:
            tables = await load_schema(db)
            logger.info("Schema Loaded: %d Tables", len(tables))
        except Exception:
            logger.warning(
                "Could not Load Schema At Startup — DB May Be Unavailable", exc_info=True
            )
    yield
    logger.info("Shutting Down Queri.ai Backend")


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
