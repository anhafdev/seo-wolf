from importlib.resources import files
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

__author__ = "@anhafxd"

SQLITE_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=30000",
)


def migrations_folder() -> str:
    return str(files("seowolf.storage") / "migrations")


def apply_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    for pragma in SQLITE_PRAGMAS:
        cursor.execute(pragma)
    cursor.close()


def create_database_engine(database_url: str) -> AsyncEngine:
    is_sqlite = database_url.startswith("sqlite")
    engine = create_async_engine(
        database_url,
        connect_args={"timeout": 30} if is_sqlite else {},
        pool_pre_ping=not is_sqlite,
    )
    if is_sqlite:
        event.listen(engine.sync_engine, "connect", apply_sqlite_pragmas)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def alembic_config(connection: Connection | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", migrations_folder())
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def upgrade_with_connection(connection: Connection) -> None:
    command.upgrade(alembic_config(connection), "head")


async def upgrade_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(upgrade_with_connection)


async def open_database(database_url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_database_engine(database_url)
    await upgrade_database(engine)
    return engine, create_session_factory(engine)
