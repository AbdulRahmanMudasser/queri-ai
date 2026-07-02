from typing import Any

# Define hardcoded role restrictions for MVP.
# Keys are roles (case-insensitive in practice, but defined nicely here).
# Values are sets of table names that the role is NOT allowed to access.
ROLE_RESTRICTIONS = {
    "staff": {"salaries"},
    "customer": {"users", "salaries", "business_rules", "few_shot_examples", "alembic_version"},
    "admin": set()  # Admin has full access to all tables
}

def apply_rbac_mask(schema: list[dict[str, Any]], role: str | None) -> list[dict[str, Any]]:
    """
    Strips unauthorized tables out of the schema array based on the user's role.
    Defaults to 'customer' (least privilege) if the role is unrecognized or None.

    This function expects `schema` to be a deepcopy or safe to filter, returning a new list.
    """
    normalized_role = (role or "customer").strip().lower()

    # Fallback to least privilege if the role is completely unknown
    if normalized_role not in ROLE_RESTRICTIONS:
        normalized_role = "customer"

    blocked_tables = ROLE_RESTRICTIONS[normalized_role]

    if not blocked_tables:
        return schema

    masked_schema = [table for table in schema if table["name"] not in blocked_tables]
    return masked_schema
