import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.reader import get_cached_schema
from app.db.session import get_db
from app.services.translator import explain, translate
from app.services.validator import limit_sql, validate_sql

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)


class QueryResponse(BaseModel):
    sql: str


class ExecuteRequest(BaseModel):
    sql: str = Field(min_length=1)


class ExecuteResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class ExplainRequest(BaseModel):
    question: str = Field(min_length=1)
    sql: str = Field(min_length=1)
    columns: list[str]
    rows: list[list[Any]]


class ExplainResponse(BaseModel):
    explanation: str


@router.post("/query/generate")
async def generate_query(body: QueryRequest) -> QueryResponse:
    logger.info("Query generate request: %s", body.question[:80])

    try:
        tables = get_cached_schema()
    except RuntimeError:
        logger.warning("Schema cache not loaded for query generation")
        raise HTTPException(status_code=503, detail="Schema not yet loaded") from None

    try:
        raw_sql = await translate(body.question, tables)
    except Exception as exc:
        logger.exception("Gemini translation failed", exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail="Translation service currently unavailable",
        ) from exc

    try:
        sql = validate_sql(raw_sql)
    except ValueError as exc:
        logger.warning("SQL validation failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from None

    return QueryResponse(sql=sql)


@router.post("/query/execute")
async def execute_query(
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    logger.info("Query execute request: %s", body.sql[:80])

    try:
        # Defense-in-depth recheck validation
        validated = validate_sql(body.sql)
        # Apply AST-level limit to prevent memory/performance issues
        limited_sql = limit_sql(validated, max_limit=100)
    except ValueError as exc:
        logger.warning("SQL validation failed before execution: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        # Execute query within a read-only transaction block with statement timeout
        async with db.begin():
            await db.execute(text("SET TRANSACTION READ ONLY"))
            await db.execute(text("SET local statement_timeout = 5000"))

            result = await db.execute(text(limited_sql))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchmany(100)]

            return ExecuteResponse(columns=columns, rows=rows)

    except DBAPIError as exc:
        orig = getattr(exc, "orig", None)
        if orig and getattr(orig, "sqlstate", None) == "57014":
            logger.warning("Query execution timed out: %s", body.sql[:200])
            raise HTTPException(
                status_code=408,
                detail="Query execution timed out (5.0s limit)",
            ) from exc
        logger.warning("Database execution error: %s", exc)
        detail = str(orig) if orig else str(exc)
        raise HTTPException(
            status_code=400,
            detail=f"Database execution error: {detail}",
        ) from exc


@router.post("/query/explain")
async def explain_query(body: ExplainRequest) -> ExplainResponse:
    logger.info("Query explain request for question: %s", body.question[:80])

    try:
        explanation = await explain(
            question=body.question,
            sql=body.sql,
            columns=body.columns,
            rows=body.rows,
        )
    except Exception as exc:
        logger.exception("Gemini explanation generation failed", exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail="Explanation service currently unavailable",
        ) from exc

    return ExplainResponse(explanation=explanation)
