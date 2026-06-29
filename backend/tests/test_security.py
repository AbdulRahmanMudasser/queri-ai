from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.translator import explain
from app.services.validator import validate_sql


class TestValidateSql:
    def test_valid_select(self) -> None:
        sql = "SELECT id, name FROM hotels WHERE id = 1"
        result = validate_sql(sql)
        assert "SELECT" in result

    def test_valid_with_cte(self) -> None:
        sql = (
            "WITH recent AS (SELECT * FROM bookings WHERE date > '2024-01-01') SELECT * FROM recent"
        )
        result = validate_sql(sql)
        assert "WITH" in result or "SELECT" in result

    def test_valid_union(self) -> None:
        sql = "SELECT name FROM hotels UNION SELECT name FROM customers"
        result = validate_sql(sql)
        assert "SELECT" in result

    def test_drop_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("DROP TABLE bookings")

    def test_delete_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("DELETE FROM bookings WHERE id = 1")

    def test_insert_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("INSERT INTO bookings (id) VALUES (1)")

    def test_update_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("UPDATE bookings SET name = 'test' WHERE id = 1")

    def test_alter_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("ALTER TABLE bookings DROP COLUMN name")

    def test_truncate_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("TRUNCATE bookings")

    def test_create_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("CREATE TABLE test (id int)")

    def test_grant_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("GRANT SELECT ON bookings TO public")

    def test_merge_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN UPDATE SET x = s.x")

    def test_stacked_queries_blocked(self) -> None:
        with pytest.raises(ValueError, match="Multiple statements"):
            validate_sql("SELECT * FROM hotels; DROP TABLE bookings")

    def test_empty_sql(self) -> None:
        with pytest.raises(ValueError, match="Empty SQL"):
            validate_sql("")

    def test_whitespace_sql(self) -> None:
        with pytest.raises(ValueError, match="Empty SQL"):
            validate_sql("   ")

    def test_invalid_syntax(self) -> None:
        with pytest.raises(ValueError, match="Invalid SQL syntax"):
            validate_sql("SELECT FROM WHERE")

    def test_commit_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("COMMIT")

    def test_rollback_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("ROLLBACK")

    def test_begin_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("BEGIN")

    def test_set_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("SET TRANSACTION READ WRITE")

    def test_show_blocked(self) -> None:
        with pytest.raises(ValueError, match="unsafe operation"):
            validate_sql("SHOW max_connections")

    def test_schema_validation_valid(self) -> None:
        sql = "SELECT name FROM hotels WHERE id = 1"
        result = validate_sql(sql, schema=MOCK_SCHEMA)
        assert "SELECT" in result

    def test_schema_validation_invalid_table(self) -> None:
        with pytest.raises(ValueError, match="Table 'non_existent' does not exist"):
            validate_sql("SELECT * FROM non_existent", schema=MOCK_SCHEMA)

    def test_schema_validation_invalid_column(self) -> None:
        with pytest.raises(ValueError, match="Column 'hotel_mail' does not exist"):
            validate_sql("SELECT hotel_mail FROM hotels", schema=MOCK_SCHEMA)

    def test_schema_validation_cte_valid(self) -> None:
        sql = "WITH recent AS (SELECT name AS hotel_name FROM hotels) SELECT hotel_name FROM recent"
        result = validate_sql(sql, schema=MOCK_SCHEMA)
        assert "SELECT" in result


MOCK_SCHEMA = [
    {
        "name": "hotels",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "character varying"},
        ],
    },
    {
        "name": "bookings",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "hotel_id", "type": "integer"},
            {"name": "booking_date", "type": "date"},
        ],
    },
]


class TestGenerateEndpoint:
    @patch("app.api.v1.endpoints.query.get_cached_schema")
    @patch("app.api.v1.endpoints.query.translate")
    def test_happy_path(
        self,
        mock_translate: object,
        mock_get_cached_schema: object,
        client: TestClient,
        mock_db_session: object,
    ) -> None:
        _ = mock_db_session
        mock_get_cached_schema.return_value = MOCK_SCHEMA
        mock_translate.return_value = {
            "sql": "SELECT name FROM hotels WHERE id = 1",
            "reasoning": "User wants hotel names",
            "tables_used": ["hotels"],
        }

        response = client.post(
            "/api/v1/query/generate",
            json={"question": "show hotels"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "sql" in data
        assert "SELECT" in data["sql"]
        assert "reasoning" in data

    @patch("app.api.v1.endpoints.query.get_cached_schema")
    @patch("app.api.v1.endpoints.query.translate")
    def test_unsafe_sql_blocked(
        self,
        mock_translate: object,
        mock_get_cached_schema: object,
        client: TestClient,
        mock_db_session: object,
    ) -> None:
        _ = mock_db_session
        mock_get_cached_schema.return_value = MOCK_SCHEMA
        mock_translate.return_value = {
            "sql": "DROP TABLE bookings",
            "reasoning": "Attempt to delete bookings",
            "tables_used": ["bookings"],
        }

        response = client.post(
            "/api/v1/query/generate",
            json={"question": "delete all bookings"},
        )
        assert response.status_code == 400
        assert "unsafe operation" in response.json()["detail"]

    @patch("app.api.v1.endpoints.query.get_cached_schema")
    def test_schema_not_loaded(
        self,
        mock_get_cached_schema: object,
        client: TestClient,
        mock_db_session: object,
    ) -> None:
        _ = mock_db_session
        mock_get_cached_schema.side_effect = RuntimeError("Schema cache not loaded")

        response = client.post(
            "/api/v1/query/generate",
            json={"question": "show hotels"},
        )
        assert response.status_code == 503

    @patch("app.api.v1.endpoints.query.get_cached_schema")
    @patch("app.api.v1.endpoints.query.translate")
    def test_gemini_error(
        self,
        mock_translate: object,
        mock_get_cached_schema: object,
        client: TestClient,
        mock_db_session: object,
    ) -> None:
        _ = mock_db_session
        mock_get_cached_schema.return_value = MOCK_SCHEMA
        mock_translate.side_effect = Exception("API error")

        response = client.post(
            "/api/v1/query/generate",
            json={"question": "show hotels"},
        )
        assert response.status_code == 503
        assert "Translation service" in response.json()["detail"]


class TestExplainCapping:
    @patch("app.services.translator._model.generate_content_async")
    @patch("app.services.translator._build_explain_prompt")
    @pytest.mark.anyio
    async def test_explain_caps_rows(
        self,
        mock_build_prompt: object,
        mock_generate: object,
    ) -> None:
        mock_generate.return_value = AsyncMock(text="Explanation")
        mock_build_prompt.return_value = "Prompt text"

        large_rows = [[i] for i in range(150)]
        await explain("question", "SELECT *", ["col"], large_rows)

        # Assert that the prompt builder was called with at most 100 rows
        mock_build_prompt.assert_called_once()
        args, _ = mock_build_prompt.call_args
        assert len(args[3]) == 100
        # verify it's the first 100 rows
        assert args[3] == [[i] for i in range(100)]
