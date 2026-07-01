from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.models import BusinessRule, FewShotExample
from app.services.context import get_business_rules, get_few_shot_examples
from app.services.embeddings import EmbeddingsProvider
from app.services.translator import _build_prompt


class DummyProvider(EmbeddingsProvider):
    async def get_embedding(self, text: str) -> list[float]:
        # Simple mocked dimension of size 3
        if "hotels" in text:
            return [1.0, 0.0, 0.0]
        elif "bookings" in text:
            return [0.0, 1.0, 0.0]
        elif "users" in text:
            return [0.0, 0.0, 1.0]
        return [0.5, 0.5, 0.0]


@pytest.mark.asyncio
async def test_get_few_shot_examples_returns_top_k() -> None:
    db = AsyncMock()
    mock_result = MagicMock()

    # Create 3 mockup few-shot examples
    ex1 = FewShotExample(
        id=1,
        question="show hotels",
        sql_query="SELECT * FROM hotels",
        question_vector=[1.0, 0.0, 0.0],
    )
    ex2 = FewShotExample(
        id=2,
        question="show bookings",
        sql_query="SELECT * FROM bookings",
        question_vector=[0.0, 1.0, 0.0],
    )
    ex3 = FewShotExample(
        id=3,
        question="show users",
        sql_query="SELECT * FROM users",
        question_vector=[0.0, 0.0, 1.0],
    )

    mock_result.scalars.return_value.all.return_value = [ex1, ex2, ex3]
    db.execute.return_value = mock_result

    provider = DummyProvider()
    # Question is closest to hotels (cosine similarity 1.0), bookings (0.0), users (0.0)
    examples = await get_few_shot_examples("show hotels query", db, provider, top_k=2)

    assert len(examples) == 2
    assert examples[0]["question"] == "show hotels"
    assert examples[0]["sql"] == "SELECT * FROM hotels"


@pytest.mark.asyncio
async def test_get_few_shot_examples_empty_db() -> None:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute.return_value = mock_result

    examples = await get_few_shot_examples("any question", db, DummyProvider())
    assert examples == []


@pytest.mark.asyncio
async def test_get_business_rules_returns_all_values() -> None:
    db = AsyncMock()
    mock_result = MagicMock()

    r1 = BusinessRule(id=1, rule_name="rule1", rule_description="desc1", rule_value="value1")
    r2 = BusinessRule(id=2, rule_name="rule2", rule_description="desc2", rule_value="value2")

    mock_result.scalars.return_value.all.return_value = [r1, r2]
    db.execute.return_value = mock_result

    rules = await get_business_rules(db)
    assert rules == ["value1", "value2"]


@pytest.mark.asyncio
async def test_get_business_rules_empty_db() -> None:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute.return_value = mock_result

    rules = await get_business_rules(db)
    assert rules == []


def test_build_prompt_includes_few_shot_section() -> None:
    examples = [{"question": "show me hotels", "sql": "SELECT * FROM hotels"}]
    prompt = _build_prompt("show hotels", "Table: hotels", few_shot_examples=examples)
    assert "## Similar Query Examples" in prompt
    assert "Q: show me hotels" in prompt
    assert "SQL: SELECT * FROM hotels" in prompt


def test_build_prompt_includes_business_rules_section() -> None:
    rules = ["1=confirmed", "status NOT IN (3)"]
    prompt = _build_prompt("show bookings", "Table: bookings", business_rules=rules)
    assert "## Business Rules" in prompt
    assert "- 1=confirmed" in prompt
    assert "- status NOT IN (3)" in prompt


def test_build_prompt_skips_sections_when_empty() -> None:
    prompt = _build_prompt(
        "show bookings", "Table: bookings", few_shot_examples=[], business_rules=[]
    )
    assert "## Similar Query Examples" not in prompt
    assert "## Business Rules" not in prompt


@patch("app.api.v1.endpoints.query.get_cached_schema")
@patch("app.api.v1.endpoints.query.get_few_shot_examples")
@patch("app.api.v1.endpoints.query.get_business_rules")
@patch("app.api.v1.endpoints.query.translate")
def test_generate_endpoint_passes_fewshot_to_translate(
    mock_translate: MagicMock,
    mock_get_business_rules: MagicMock,
    mock_get_few_shot_examples: MagicMock,
    mock_get_cached_schema: MagicMock,
    client: TestClient,
    mock_db_session: AsyncMock,
) -> None:
    # Set up mocks
    mock_get_cached_schema.return_value = [
        {"name": "hotels", "columns": [{"name": "id", "type": "integer"}]}
    ]
    mock_get_few_shot_examples.return_value = [{"question": "most bookings", "sql": "SELECT 1"}]
    mock_get_business_rules.return_value = ["rule1"]
    mock_translate.return_value = {
        "sql": "SELECT * FROM hotels",
        "reasoning": "Translation mock reasoning",
        "tables_used": ["hotels"],
    }

    # EXPLAIN dry-run execute mock
    mock_db_session.execute.return_value = AsyncMock()

    response = client.post(
        "/api/v1/query/generate",
        json={"question": "show me hotels"},
    )
    assert response.status_code == 200

    # Assert few-shot and rules were fetched and passed to translate
    mock_get_few_shot_examples.assert_called_once()
    mock_get_business_rules.assert_called_once()
    mock_translate.assert_called_once()
    _, kwargs = mock_translate.call_args
    assert kwargs.get("few_shot_examples") == [{"question": "most bookings", "sql": "SELECT 1"}]
    assert kwargs.get("business_rules") == ["rule1"]


@patch("app.api.v1.endpoints.query.get_cached_schema")
@patch("app.api.v1.endpoints.query.get_few_shot_examples")
@patch("app.api.v1.endpoints.query.get_business_rules")
@patch("app.api.v1.endpoints.query.translate")
def test_generate_endpoint_fallback_on_fetch_error(
    mock_translate: MagicMock,
    mock_get_business_rules: MagicMock,
    mock_get_few_shot_examples: MagicMock,
    mock_get_cached_schema: MagicMock,
    client: TestClient,
    mock_db_session: AsyncMock,
) -> None:
    # Set up mocks
    mock_get_cached_schema.return_value = [
        {"name": "hotels", "columns": [{"name": "id", "type": "integer"}]}
    ]
    # Simulate DB fetch failure
    mock_get_few_shot_examples.side_effect = RuntimeError("DB connection lost")
    mock_get_business_rules.return_value = ["rule1"]
    mock_translate.return_value = {
        "sql": "SELECT * FROM hotels",
        "reasoning": "Translation mock reasoning",
        "tables_used": ["hotels"],
    }

    # EXPLAIN dry-run execute mock
    mock_db_session.execute.return_value = AsyncMock()

    response = client.post(
        "/api/v1/query/generate",
        json={"question": "show me hotels"},
    )
    # Endpoint should handle error gracefully and fallback to empty list context
    assert response.status_code == 200
    mock_translate.assert_called_once()
    _, kwargs = mock_translate.call_args
    assert kwargs.get("few_shot_examples") == []
    assert kwargs.get("business_rules") == []
