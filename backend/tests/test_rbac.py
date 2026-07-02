import pytest

from app.core.rbac import apply_rbac_mask


@pytest.fixture
def sample_schema() -> list[dict[str, str | list[dict[str, str]]]]:
    return [
        {"name": "users", "columns": [{"name": "id", "type": "int"}]},
        {"name": "salaries", "columns": [{"name": "amount", "type": "int"}]},
        {"name": "public_data", "columns": [{"name": "info", "type": "str"}]},
    ]


def test_apply_rbac_mask_staff(sample_schema: list[dict[str, str | list[dict[str, str]]]]) -> None:
    # Staff cannot see salaries, but can see users and public_data
    masked = apply_rbac_mask(sample_schema, role="staff")
    table_names = [t["name"] for t in masked]

    assert "salaries" not in table_names
    assert "users" in table_names
    assert "public_data" in table_names


def test_apply_rbac_mask_customer(
    sample_schema: list[dict[str, str | list[dict[str, str]]]]
) -> None:
    # Customer cannot see users or salaries
    masked = apply_rbac_mask(sample_schema, role="customer")
    table_names = [t["name"] for t in masked]

    assert "salaries" not in table_names
    assert "users" not in table_names
    assert "public_data" in table_names


def test_apply_rbac_mask_admin(sample_schema: list[dict[str, str | list[dict[str, str]]]]) -> None:
    # Admin sees everything
    masked = apply_rbac_mask(sample_schema, role="admin")
    table_names = [t["name"] for t in masked]

    assert "salaries" in table_names
    assert "users" in table_names
    assert "public_data" in table_names


def test_apply_rbac_mask_default_fallback(
    sample_schema: list[dict[str, str | list[dict[str, str]]]]
) -> None:
    # Unknown roles or None fallback to customer
    for role in [None, "unknown", "", "   "]:
        masked = apply_rbac_mask(sample_schema, role=role)  # type: ignore[arg-type]
        table_names = [t["name"] for t in masked]

        assert "salaries" not in table_names
        assert "users" not in table_names
        assert "public_data" in table_names
