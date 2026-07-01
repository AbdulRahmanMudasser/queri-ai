import json
import logging
from typing import Any, cast

import google.generativeai as genai
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
_model = genai.GenerativeModel("models/gemini-2.5-flash-lite")  # type: ignore[attr-defined]


class TranslationResponse(BaseModel):
    reasoning: str = Field(description="Explanation of translation logic")
    sql: str = Field(description="The generated PostgreSQL query")
    tables_used: list[str] = Field(description="List of tables used in the SQL query")


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


def _build_prompt(
    question: str,
    schema_md: str,
    few_shot_examples: list[dict[str, str]] | None = None,
    business_rules: list[str] | None = None,
) -> str:
    rules_section = ""
    if business_rules:
        rules_lines = "\n".join(f"- {r}" for r in business_rules)
        rules_section = f"\n## Business Rules\n{rules_lines}\n"

    fewshot_section = ""
    if few_shot_examples:
        examples = "\n\n".join(f"Q: {ex['question']}\nSQL: {ex['sql']}" for ex in few_shot_examples)
        fewshot_section = f"\n## Similar Query Examples\n{examples}\n"

    return f"""{_SYSTEM_PROMPT}

Database schema:
{schema_md}
{rules_section}{fewshot_section}
Rules:
1. Generate ONLY SELECT statements (or WITH ... SELECT for CTEs)
2. NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, GRANT, REVOKE, or CREATE
3. NEVER generate multiple statements
4. Use proper PostgreSQL syntax
5. If the question cannot be answered with a SELECT, respond with sql as "-- unable to answer"

User question: {question}

Return response matching the structured JSON response schema."""


def _build_correction_prompt(
    question: str,
    schema_md: str,
    previous_sql: str,
    error_message: str,
    few_shot_examples: list[dict[str, str]] | None = None,
    business_rules: list[str] | None = None,
) -> str:
    rules_section = ""
    if business_rules:
        rules_lines = "\n".join(f"- {r}" for r in business_rules)
        rules_section = f"\n## Business Rules\n{rules_lines}\n"

    fewshot_section = ""
    if few_shot_examples:
        examples = "\n\n".join(f"Q: {ex['question']}\nSQL: {ex['sql']}" for ex in few_shot_examples)
        fewshot_section = f"\n## Similar Query Examples\n{examples}\n"

    return f"""You are a PostgreSQL expert assistant.
The previous SQL query you generated for the user's question failed validation or execution.
Correct the query and return a valid PostgreSQL query.

Database schema:
{schema_md}
{rules_section}{fewshot_section}
User's Original Question: {question}
Failed SQL Query: {previous_sql}
Error Message: {error_message}

Rules:
1. Generate ONLY SELECT statements (or WITH ... SELECT for CTEs)
2. NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, GRANT, REVOKE, or CREATE
3. NEVER generate multiple statements
4. Use proper PostgreSQL syntax
5. Fix the error described in the error message.
   Ensure all table and column names exist in the schema.

Return response matching the structured JSON response schema."""


async def translate(
    question: str,
    schema: list[dict[str, Any]],
    previous_sql: str | None = None,
    error_message: str | None = None,
    few_shot_examples: list[dict[str, str]] | None = None,
    business_rules: list[str] | None = None,
) -> dict[str, Any]:
    schema_md = _format_schema(schema)
    if previous_sql and error_message:
        prompt = _build_correction_prompt(
            question,
            schema_md,
            previous_sql,
            error_message,
            few_shot_examples=few_shot_examples,
            business_rules=business_rules,
        )
    else:
        prompt = _build_prompt(
            question,
            schema_md,
            few_shot_examples=few_shot_examples,
            business_rules=business_rules,
        )

    logger.info(
        "Translation Prompt Constructed: %d Tables Included In Schema Context, "
        "Total Prompt Length: %d Characters",
        len(schema),
        len(prompt),
    )
    logger.info("Sending Prompt To Gemini (Question=%s)", question[:80])
    response = await _model.generate_content_async(
        prompt,
        generation_config={  # type: ignore[arg-type]
            "response_mime_type": "application/json",
            "response_schema": TranslationResponse,
        },
    )
    if response.text is None:
        raise RuntimeError("Gemini blocked the response (safety filter)")

    try:
        result = cast(dict[str, Any], json.loads(response.text))
    except Exception as exc:
        logger.error("Failed To Parse Gemini Structured JSON: %s", response.text)
        raise RuntimeError("Gemini returned invalid JSON structure") from exc

    logger.info("Gemini Returned Structured SQL: %s", result.get("sql", "")[:200])
    return result


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
    logger.info("Sending Explain Prompt To Gemini (Question=%s)", question[:80])
    response = await _model.generate_content_async(prompt)
    if response.text is None:
        raise RuntimeError("Gemini blocked the response (safety filter)")
    return str(response.text).strip()
