from typing import Any

import sqlglot
from sqlglot import exp

_BLOCKED_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
    exp.Grant,
    exp.Create,
    exp.Merge,
    exp.Command,
    exp.Commit,
    exp.Rollback,
    exp.Transaction,
    exp.Set,
    exp.Show,
)


def validate_sql(sql: str, schema: list[dict[str, Any]] | None = None) -> str:
    if not sql.strip():
        raise ValueError("Empty SQL query")

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Invalid SQL syntax: {e}") from e

    statements = [stmt for stmt in statements if stmt is not None]

    if len(statements) > 1:
        raise ValueError("Multiple statements are not allowed (stacked queries)")

    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Invalid SQL syntax: {e}") from e

    for node in parsed.walk():
        if isinstance(node, _BLOCKED_NODES):
            raise ValueError(f"Query contains unsafe operation: {node.sql()}")

    # Table and Column validation against cached schema
    if schema is not None:
        db_schema = {
            table["name"]: {col["name"]: col.get("type", "UNKNOWN") for col in table["columns"]}
            for table in schema
        }

        ctes = {cte.alias for cte in parsed.find_all(exp.CTE) if cte.alias}
        for table_node in parsed.find_all(exp.Table):
            if table_node.name not in db_schema and table_node.name not in ctes:
                raise ValueError(f"Table '{table_node.name}' does not exist in database schema")

        try:
            from sqlglot.optimizer.qualify import qualify
            parsed = qualify(parsed, schema=db_schema, dialect="postgres")
        except sqlglot.errors.OptimizeError as e:
            raise ValueError(f"Query validation failed: {e}") from e

    return sqlglot.transpile(
        parsed.sql(dialect="postgres"), read="postgres", write="postgres", pretty=True
    )[0]


def limit_sql(sql: str, max_limit: int = 100) -> str:
    parsed = sqlglot.parse_one(sql, read="postgres")
    limit_node = parsed.args.get("limit")
    if limit_node:
        try:
            val = int(limit_node.expression.this)
            if val > max_limit:
                limit_node.expression.replace(exp.Literal.number(max_limit))
        except Exception:
            limit_node.expression.replace(exp.Literal.number(max_limit))
    else:
        if hasattr(parsed, "limit"):
            parsed = parsed.limit(max_limit)
    return parsed.sql(dialect="postgres", pretty=True)
