from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

MOCK_SCHEMA = [
    {
        "name": "hotels",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "character varying"},
        ],
    }
]


class TestQuerySelfCorrection:
    @patch("app.api.v1.endpoints.query.get_cached_schema")
    @patch("app.api.v1.endpoints.query.translate")
    def test_correction_on_validation_failure(
        self,
        mock_translate: AsyncMock,
        mock_get_cached_schema: MagicMock,
        client: TestClient,
        mock_db_session: AsyncMock,
    ) -> None:
        _ = mock_db_session
        mock_get_cached_schema.return_value = MOCK_SCHEMA

        # First call returns invalid column (hotel_mail)
        # Second call returns valid column (name)
        mock_translate.side_effect = [
            {
                "sql": "SELECT hotel_mail FROM hotels",
                "reasoning": "Incorrect column selection",
                "tables_used": ["hotels"],
            },
            {
                "sql": "SELECT name FROM hotels",
                "reasoning": "Corrected column selection",
                "tables_used": ["hotels"],
            },
        ]

        response = client.post(
            "/api/v1/query/generate",
            json={"question": "show hotel names"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sql"] == "SELECT\n  name\nFROM hotels"
        assert data["reasoning"] == "Corrected column selection"

        # Verify translate was called exactly twice
        assert mock_translate.call_count == 2
        # Verify the second call received the error message feedback
        args, kwargs = mock_translate.call_args_list[1]
        assert "hotel_mail" in kwargs.get("error_message", "")
        assert kwargs.get("previous_sql") == "SELECT hotel_mail FROM hotels"

    @patch("app.api.v1.endpoints.query.get_cached_schema")
    @patch("app.api.v1.endpoints.query.translate")
    def test_correction_on_dbapi_error(
        self,
        mock_translate: AsyncMock,
        mock_get_cached_schema: MagicMock,
        client: TestClient,
        mock_db_session: AsyncMock,
    ) -> None:
        mock_get_cached_schema.return_value = MOCK_SCHEMA

        # First call returns SQL with invalid aggregate function in WHERE clause
        # Second call returns valid SQL
        mock_translate.side_effect = [
            {
                "sql": "SELECT name FROM hotels WHERE COUNT(id) > 1",
                "reasoning": "Incorrect aggregate in WHERE",
                "tables_used": ["hotels"],
            },
            {
                "sql": "SELECT name FROM hotels",
                "reasoning": "Corrected query",
                "tables_used": ["hotels"],
            },
        ]

        # Setup mock db to raise DBAPIError only when aggregate query is dry-run (EXPLAIN)
        orig_exc = Exception("aggregate functions are not allowed in WHERE")
        orig_exc.sqlstate = "42803"
        db_error = DBAPIError("EXPLAIN SELECT name FROM hotels WHERE COUNT(id) > 1", {}, orig_exc)

        async def mock_execute_side_effect(
            statement: object,
            *_args: object,
            **_kwargs: object,
        ) -> MagicMock:
            stmt_str = str(statement)
            if "COUNT(id)" in stmt_str:
                raise db_error
            return MagicMock()

        mock_db_session.execute.side_effect = mock_execute_side_effect

        response = client.post(
            "/api/v1/query/generate",
            json={"question": "show hotels with many bookings"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "SELECT" in data["sql"]
        assert data["reasoning"] == "Corrected query"

        # Verify translate was called exactly twice
        assert mock_translate.call_count == 2
        args, kwargs = mock_translate.call_args_list[1]
        assert "aggregate functions" in kwargs.get("error_message", "")

    @patch("app.api.v1.endpoints.query.get_cached_schema")
    @patch("app.api.v1.endpoints.query.translate")
    def test_correction_failure_raises_400(
        self,
        mock_translate: AsyncMock,
        mock_get_cached_schema: MagicMock,
        client: TestClient,
        mock_db_session: AsyncMock,
    ) -> None:
        _ = mock_db_session
        mock_get_cached_schema.return_value = MOCK_SCHEMA

        # Both attempts return invalid column names
        mock_translate.return_value = {
            "sql": "SELECT hotel_mail FROM hotels",
            "reasoning": "Incorrect column selection",
            "tables_used": ["hotels"],
        }

        response = client.post(
            "/api/v1/query/generate",
            json={"question": "show hotels"},
        )
        assert response.status_code == 400
        assert "Query generation and correction failed" in response.json()["detail"]
        assert "hotel_mail" in response.json()["detail"]

        # Verify translate was called twice (initial + retry)
        assert mock_translate.call_count == 2
