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


def validate_sql(sql: str) -> str:
    if not sql.strip():
        raise ValueError("Empty SQL query")

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Invalid SQL syntax: {e}") from e

    if len(statements) > 1:
        raise ValueError("Multiple statements are not allowed (stacked queries)")

    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Invalid SQL syntax: {e}") from e

    for node in parsed.walk():
        if isinstance(node, _BLOCKED_NODES):
            raise ValueError(f"Query contains unsafe operation: {node.sql()}")

    return sqlglot.transpile(sql, read="postgres", write="postgres", pretty=True)[0]


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
