from typing import Any

from sqlalchemy import Insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

__author__ = "@anhafxd"


def insert_skipping_duplicates(model: Any, dialect_name: str) -> Insert:
    if dialect_name == "postgresql":
        return postgres_insert(model).on_conflict_do_nothing()
    if dialect_name == "sqlite":
        return sqlite_insert(model).on_conflict_do_nothing()
    raise ValueError(f"unsupported database dialect: {dialect_name}")


async def add_rows_skipping_duplicates(
    session: AsyncSession, model: Any, rows: list[dict[str, Any]]
) -> None:
    if not rows:
        return
    statement = insert_skipping_duplicates(model, session.bind.dialect.name)
    await session.execute(statement, rows)
