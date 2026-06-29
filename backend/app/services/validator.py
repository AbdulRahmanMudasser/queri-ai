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
        db_schema = {table["name"]: {col["name"] for col in table["columns"]} for table in schema}
        ctes = {cte.alias for cte in parsed.find_all(exp.CTE) if cte.alias}

        alias_to_table = {}
        referenced_tables = set()

        # 1. Collect all referenced tables and map their aliases
        for table_node in parsed.find_all(exp.Table):
            table_name = table_node.name
            if table_name in ctes:
                continue

            if table_name not in db_schema:
                raise ValueError(f"Table '{table_name}' does not exist in database schema")

            referenced_tables.add(table_name)
            alias_to_table[table_name] = table_name
            if table_node.alias:
                alias_to_table[table_node.alias] = table_name

        # 2. Collect all select aliases in the query to allow referencing them
        select_aliases = {
            alias_node.alias
            for alias_node in parsed.find_all(exp.Alias)
            if alias_node.alias
        }

        # 3. Verify all column nodes
        for column_node in parsed.find_all(exp.Column):
            col_name = column_node.name
            col_table = column_node.table

            # Skip wildcards (e.g. table.*)
            if col_name == "*":
                continue

            if col_table:
                if col_table in ctes:
                    continue

                actual_table = alias_to_table.get(col_table)
                if actual_table:
                    if col_name not in db_schema[actual_table]:
                        raise ValueError(
                            f"Column '{col_name}' does not exist in table '{actual_table}'"
                        )
                else:
                    # Ignore subquery aliases or unrecognized table prefixes
                    pass
            else:
                if referenced_tables:
                    in_any_table = any(col_name in db_schema[t] for t in referenced_tables)
                    if not in_any_table and col_name not in select_aliases:
                        raise ValueError(f"Column '{col_name}' does not exist in referenced tables")

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
