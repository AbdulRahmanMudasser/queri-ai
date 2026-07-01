import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.reader import get_cached_schema
from app.db.session import get_db
from app.services.context import get_business_rules, get_few_shot_examples, prune_schema
from app.services.embeddings import get_embeddings_provider
from app.services.translator import explain, translate
from app.services.validator import limit_sql, validate_sql

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)


class QueryResponse(BaseModel):
    sql: str
    reasoning: str


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
async def generate_query(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    logger.info("Query Generate Request: %s", body.question[:80])

    try:
        tables = get_cached_schema()
    except RuntimeError:
        logger.warning("Schema Cache Not Loaded For Query Generation")
        raise HTTPException(status_code=503, detail="Schema not yet loaded") from None

    provider = get_embeddings_provider()
    try:
        pruned_tables = await prune_schema(body.question, tables, provider)
    except Exception as exc:
        logger.warning("Schema Pruning Failed, Falling Back To Top 10 Tables: %s", exc)
        pruned_tables = tables[:10] if tables else []

    try:
        few_shot = await get_few_shot_examples(body.question, db, provider)
        rules = await get_business_rules(db)
        logger.info(
            "Fetched %d Few-Shot Examples And %d Business Rules For Question: %s",
            len(few_shot),
            len(rules),
            body.question[:80],
        )
    except Exception as exc:
        logger.warning("Few-Shot/Rules Fetch Failed, Proceeding With Empty Context: %s", exc)
        few_shot, rules = [], []

    try:
        # Initial attempt
        translation = await translate(
            body.question,
            pruned_tables,
            few_shot_examples=few_shot,
            business_rules=rules,
        )
        raw_sql = translation["sql"]
        reasoning = translation["reasoning"]

        # Validate against safety rules and table/column schema catalog
        sql = validate_sql(raw_sql, tables)

        # Dry-run execution using EXPLAIN within a read-only transaction block
        async with db.begin():
            await db.execute(text("SET TRANSACTION READ ONLY"))
            await db.execute(text("SET local statement_timeout = 2000"))
            await db.execute(text(f"EXPLAIN {sql}"))

    except (ValueError, DBAPIError) as exc:
        logger.warning(
            "Initial Query Generation Failed Validation Or Dry-Run, Initiating Self-Correction: %s",
            exc,
        )

        # Prepare the feedback error message for Gemini
        if isinstance(exc, DBAPIError):
            orig = getattr(exc, "orig", None)
            error_msg = str(orig) if orig else str(exc)
        else:
            error_msg = str(exc)

        # Attempt self-correction (exactly 1 retry)
        try:
            # We must pass the original failed raw_sql and the error message
            failed_sql = raw_sql if "raw_sql" in locals() else ""
            correction = await translate(
                body.question,
                pruned_tables,
                previous_sql=failed_sql,
                error_message=error_msg,
                few_shot_examples=few_shot,
                business_rules=rules,
            )
            raw_sql = correction["sql"]
            reasoning = correction["reasoning"]

            # Re-validate against safety rules and table/column schema catalog
            sql = validate_sql(raw_sql, tables)

            # Re-run dry-run execution
            async with db.begin():
                await db.execute(text("SET TRANSACTION READ ONLY"))
                await db.execute(text("SET local statement_timeout = 2000"))
                await db.execute(text(f"EXPLAIN {sql}"))

        except Exception as retry_exc:
            logger.exception("Query Self-Correction Retry Failed", exc_info=retry_exc)
            err_detail = (
                str(getattr(retry_exc, "orig", retry_exc))
                if isinstance(retry_exc, DBAPIError)
                else str(retry_exc)
            )
            raise HTTPException(
                status_code=400,
                detail=f"Query generation and correction failed: {err_detail}",
            ) from retry_exc

    except Exception as exc:
        logger.exception("Gemini Translation Failed With Unexpected Error", exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail="Translation service currently unavailable",
        ) from exc

    return QueryResponse(sql=sql, reasoning=reasoning)


@router.post("/query/execute")
async def execute_query(
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    logger.info("Query Execute Request: %s", body.sql[:80])

    try:
        tables = get_cached_schema()
    except RuntimeError:
        logger.warning("Schema Cache Not Loaded For Query Execution")
        raise HTTPException(status_code=503, detail="Schema not yet loaded") from None

    try:
        # Defense-in-depth recheck validation
        validated = validate_sql(body.sql, tables)
        # Apply AST-level limit to prevent memory/performance issues
        limited_sql = limit_sql(validated, max_limit=100)
    except ValueError as exc:
        logger.warning("SQL Validation Failed Before Execution: %s", exc)
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
            logger.warning("Query Execution Timed Out: %s", body.sql[:200])
            raise HTTPException(
                status_code=408,
                detail="Query execution timed out (5.0s limit)",
            ) from exc
        logger.warning("Database Execution Error: %s", exc)
        detail = str(orig) if orig else str(exc)
        raise HTTPException(
            status_code=400,
            detail=f"Database execution error: {detail}",
        ) from exc


@router.post("/query/explain")
async def explain_query(body: ExplainRequest) -> ExplainResponse:
    logger.info("Query Explain Request For Question: %s", body.question[:80])

    try:
        explanation = await explain(
            question=body.question,
            sql=body.sql,
            columns=body.columns,
            rows=body.rows,
        )
    except Exception as exc:
        logger.exception("Gemini Explanation Generation Failed", exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail="Explanation service currently unavailable",
        ) from exc

    return ExplainResponse(explanation=explanation)
