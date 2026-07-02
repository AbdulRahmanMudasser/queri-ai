from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "development"


class MockResult:
    def __init__(self, keys: list[str], rows: list[tuple[object, ...]]):
        self._keys = keys
        self._rows = rows

    def keys(self) -> list[str]:
        return self._keys

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        return self._rows[:size]


MOCK_SCHEMA = [
    {
        "name": "hotels",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "character varying"},
            {"name": "city", "type": "character varying"},
        ],
    },
    {
        "name": "bookings",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "hotel_id", "type": "integer"},
        ],
    },
    {
        "name": "non_existent_table",
        "columns": [
            {"name": "id", "type": "integer"},
        ],
    },
]


@patch("app.api.v1.endpoints.query.get_cached_schema", new_callable=AsyncMock)
def test_execute_query_happy_path(
    mock_get_cached_schema: object,
    client: TestClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_get_cached_schema.return_value = MOCK_SCHEMA
    mock_db_session.execute.return_value = MockResult(
        ["name", "city"],
        [("Marriott", "Lahore"), ("Pearl Continental", "Lahore")],
    )

    response = client.post(
        "/api/v1/query/execute",
        json={"sql": "SELECT name, city FROM hotels WHERE city = 'Lahore'"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["columns"] == ["name", "city"]
    assert data["rows"] == [
        ["Marriott", "Lahore"],
        ["Pearl Continental", "Lahore"],
    ]
    # Verify that local statement_timeout and READ ONLY transaction settings were executed
    assert mock_db_session.execute.call_count >= 3


@patch("app.api.v1.endpoints.query.get_cached_schema", new_callable=AsyncMock)
def test_execute_query_unsafe(
    mock_get_cached_schema: object,
    client: TestClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_get_cached_schema.return_value = MOCK_SCHEMA
    response = client.post(
        "/api/v1/query/execute",
        json={"sql": "DROP TABLE bookings"},
    )
    assert response.status_code == 400
    assert "unsafe operation" in response.json()["detail"]
    assert mock_db_session.execute.call_count == 0


@patch("app.api.v1.endpoints.query.get_cached_schema", new_callable=AsyncMock)
def test_execute_query_syntax_error(
    mock_get_cached_schema: object,
    client: TestClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_get_cached_schema.return_value = MOCK_SCHEMA
    orig_exc = Exception('syntax error at or near "FROM"')
    orig_exc.sqlstate = "42601"  # syntax error code

    async def mock_execute(statement: object, *_args: object, **_kwargs: object) -> MockResult:
        stmt_str = str(statement)
        if "SELECT" in stmt_str:
            raise DBAPIError(stmt_str, {}, orig_exc)
        return MockResult([], [])

    mock_db_session.execute.side_effect = mock_execute

    response = client.post(
        "/api/v1/query/execute",
        json={"sql": "SELECT * FROM non_existent_table"},
    )
    assert response.status_code == 400
    assert "Database execution error" in response.json()["detail"]


@patch("app.api.v1.endpoints.query.get_cached_schema", new_callable=AsyncMock)
def test_execute_query_timeout(
    mock_get_cached_schema: object,
    client: TestClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_get_cached_schema.return_value = MOCK_SCHEMA
    orig_exc = Exception("canceling statement due to statement timeout")
    orig_exc.sqlstate = "57014"  # timeout code

    async def mock_execute(statement: object, *_args: object, **_kwargs: object) -> MockResult:
        stmt_str = str(statement)
        if "SELECT" in stmt_str:
            raise DBAPIError(stmt_str, {}, orig_exc)
        return MockResult([], [])

    mock_db_session.execute.side_effect = mock_execute

    response = client.post(
        "/api/v1/query/execute",
        json={"sql": "SELECT * FROM bookings"},
    )
    assert response.status_code == 408
    assert "timed out" in response.json()["detail"]


@patch("app.api.v1.endpoints.query.explain")
def test_explain_query_happy_path(mock_explain: AsyncMock, client: TestClient) -> None:
    mock_explain.return_value = "There are 2 hotels in Lahore."

    response = client.post(
        "/api/v1/query/explain",
        json={
            "question": "show hotels",
            "sql": "SELECT name, city FROM hotels",
            "columns": ["name", "city"],
            "rows": [["Marriott", "Lahore"], ["Pearl Continental", "Lahore"]],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["explanation"] == "There are 2 hotels in Lahore."


@patch("app.api.v1.endpoints.query.explain")
def test_explain_query_api_error(mock_explain: AsyncMock, client: TestClient) -> None:
    mock_explain.side_effect = Exception("Gemini error")

    response = client.post(
        "/api/v1/query/explain",
        json={
            "question": "show hotels",
            "sql": "SELECT name, city FROM hotels",
            "columns": ["name", "city"],
            "rows": [],
        },
    )
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]
