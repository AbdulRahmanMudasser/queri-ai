"""Baseline

Revision ID: 69d6258e32e8
Revises: None
Create Date: 2026-07-02 08:22:39.697962

"""
from collections.abc import Sequence

import pgvector.sqlalchemy  # type: ignore[import-untyped]
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '69d6258e32e8'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create the vector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Create business_rules
    op.create_table('business_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rule_name', sa.String(), nullable=False),
        sa.Column('rule_description', sa.String(), nullable=False),
        sa.Column('rule_value', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create few_shot_examples
    op.create_table('few_shot_examples',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question', sa.String(), nullable=False),
        sa.Column('sql_query', sa.String(), nullable=False),
        sa.Column('question_vector', pgvector.sqlalchemy.vector.VECTOR(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('few_shot_examples')
    op.drop_table('business_rules')
    op.execute("DROP EXTENSION IF EXISTS vector")
