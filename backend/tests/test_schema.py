from unittest.mock import patch

from fastapi.testclient import TestClient


def test_schema_endpoint_returns_503_when_cache_empty(client: TestClient) -> None:
    response = client.get("/api/v1/schema")
    assert response.status_code == 503


@patch("app.api.v1.endpoints.schema.get_cached_schema")
def test_schema_endpoint_returns_tables(
    mock_get_cached_schema: object, client: TestClient
) -> None:
    mock_get_cached_schema.return_value = [
        {
            "name": "hotels",
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "character varying"},
            ],
        }
    ]
    response = client.get("/api/v1/schema")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    assert len(data["tables"]) == 1
    assert data["tables"][0]["name"] == "hotels"
