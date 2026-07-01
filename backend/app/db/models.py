from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BusinessRule(Base):
    __tablename__ = "business_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String, nullable=False)
    rule_description: Mapped[str] = mapped_column(String, nullable=False)
    rule_value: Mapped[str] = mapped_column(String, nullable=False)


class FewShotExample(Base):
    __tablename__ = "few_shot_examples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    sql_query: Mapped[str] = mapped_column(String, nullable=False)
    question_vector: Mapped[list[float]] = mapped_column(Vector(), nullable=False)
