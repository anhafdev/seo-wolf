import asyncio

from alembic import context
from sqlalchemy import Connection

from seowolf.settings import load_settings
from seowolf.storage.database import create_database_engine
from seowolf.storage.schema import schema_metadata

__author__ = "@anhafxd"


def run_with_connection(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=schema_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_with_new_engine() -> None:
    engine = create_database_engine(load_settings().resolved_database_url())
    async with engine.begin() as connection:
        await connection.run_sync(run_with_connection)
    await engine.dispose()


def run_offline() -> None:
    context.configure(
        url=load_settings().resolved_database_url(),
        target_metadata=schema_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    shared_connection = context.config.attributes.get("connection")
    if shared_connection is None:
        asyncio.run(run_with_new_engine())
    else:
        run_with_connection(shared_connection)


if context.is_offline_mode():
    run_offline()
else:
    run_online()
