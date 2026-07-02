import json
import logging
import os
from typing import Any, cast

import google.generativeai as genai
import jinja2
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
_model = genai.GenerativeModel(settings.LLM_MODEL_NAME)  # type: ignore[attr-defined]

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "..", "templates", "prompts")),
    trim_blocks=True,
    lstrip_blocks=True,
)


class TranslationResponse(BaseModel):
    reasoning: str = Field(description="Explanation of translation logic")
    sql: str = Field(description="The generated PostgreSQL query")
    tables_used: list[str] = Field(description="List of tables used in the SQL query")


async def translate(
    question: str,
    schema: list[dict[str, Any]],
    previous_sql: str | None = None,
    error_message: str | None = None,
    few_shot_examples: list[dict[str, str]] | None = None,
    business_rules: list[str] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if previous_sql and error_message:
        template = jinja_env.get_template("correct.j2")
        prompt = template.render(
            question=question,
            schema=schema,
            previous_sql=previous_sql,
            error_message=error_message,
            few_shot_examples=few_shot_examples,
            business_rules=business_rules,
            history=history,
        )
    else:
        template = jinja_env.get_template("generate.j2")
        prompt = template.render(
            question=question,
            schema=schema,
            few_shot_examples=few_shot_examples,
            business_rules=business_rules,
            history=history,
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


async def explain(question: str, sql: str, columns: list[str], rows: list[list[Any]]) -> str:
    # Cap rows to MAX_ROW_LIMIT to prevent prompt size blowup
    capped_rows = rows[:settings.MAX_ROW_LIMIT]
    template = jinja_env.get_template("explain.j2")
    prompt = template.render(
        question=question,
        sql=sql,
        columns=columns,
        rows=capped_rows,
    )

    logger.info("Sending Explain Prompt To Gemini (Question=%s)", question[:80])
    response = await _model.generate_content_async(prompt)
    if response.text is None:
        raise RuntimeError("Gemini blocked the response (safety filter)")
    return str(response.text).strip()
