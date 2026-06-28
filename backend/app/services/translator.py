import logging
from typing import Any

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
_model = genai.GenerativeModel("models/gemini-2.5-flash-lite")  # type: ignore[attr-defined]


def _format_schema(schema: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for table in schema:
        cols = "\n".join(f"  - {c['name']} ({c['type']})" for c in table["columns"])
        lines.append(f"Table: {table['name']}\n{cols}")
    return "\n\n".join(lines)


_SYSTEM_PROMPT = (
    "You are a PostgreSQL expert assistant. "
    "Convert natural language questions into safe, read-only SQL queries."
)


def _build_prompt(question: str, schema_md: str) -> str:
    return f"""{_SYSTEM_PROMPT}

Database schema:
{schema_md}

Rules:
1. Generate ONLY SELECT statements (or WITH ... SELECT for CTEs)
2. NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, GRANT, REVOKE, or CREATE
3. NEVER generate multiple statements
4. Return ONLY the raw SQL - no explanations, no markdown formatting, no code fences
5. Use proper PostgreSQL syntax
6. If the question cannot be answered with a SELECT, respond with "-- unable to answer"

User question: {question}

SQL:"""


def _strip_markdown(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        first_nl = sql.find("\n")
        if first_nl == -1:
            return ""
        sql = sql[first_nl + 1 :]
        if sql.endswith("```"):
            sql = sql[:-3]
    return sql.strip()


async def translate(question: str, schema: list[dict[str, Any]]) -> str:
    schema_md = _format_schema(schema)
    prompt = _build_prompt(question, schema_md)
    logger.info("Sending prompt to Gemini (question=%s)", question[:80])
    response = await _model.generate_content_async(prompt)
    if response.text is None:
        raise RuntimeError("Gemini blocked the response (safety filter)")
    sql = _strip_markdown(response.text)
    logger.info("Gemini returned SQL: %s", sql[:200])
    return sql


_EXPLAIN_SYSTEM_PROMPT = (
    "You are a helpful data analyst assistant. "
    "Your task is to explain the results of a database query in clear, natural English."
)


def _build_explain_prompt(
    question: str, sql: str, columns: list[str], rows: list[list[Any]]
) -> str:
    data_str = ""
    if not rows:
        data_str = "No rows returned."
    else:
        headers = " | ".join(columns)
        divider = " | ".join(["---"] * len(columns))
        row_lines = [" | ".join(map(str, r)) for r in rows]
        data_str = f"| {headers} |\n| {divider} |\n" + "\n".join(f"| {rl} |" for rl in row_lines)

    return f"""{_EXPLAIN_SYSTEM_PROMPT}

User's Original Question: {question}
SQL Query Executed: {sql}

Query Results:
{data_str}

Provide a concise, user-friendly summary of these results in natural English
that directly answers the user's question. Do not explain the SQL syntax
or structure unless requested, just focus on what the data shows.
"""


async def explain(question: str, sql: str, columns: list[str], rows: list[list[Any]]) -> str:
    # Cap rows to 100 to prevent prompt size blowup
    capped_rows = rows[:100]
    prompt = _build_explain_prompt(question, sql, columns, capped_rows)
    logger.info("Sending explain prompt to Gemini (question=%s)", question[:80])
    response = await _model.generate_content_async(prompt)
    if response.text is None:
        raise RuntimeError("Gemini blocked the response (safety filter)")
    return str(response.text).strip()

