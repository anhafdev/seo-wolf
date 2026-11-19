from pathlib import Path

from sqlalchemy import inspect, text

from seowolf.settings import WolfSettings
from seowolf.storage.database import open_database
from seowolf.storage.models_base import url_key

__author__ = "@anhafxd"

EXPECTED_TABLES = {
    "projects",
    "crawls",
    "frontier",
    "robots_files",
    "pages",
    "links",
    "redirects",
    "resources",
    "sitemap_files",
    "sitemap_urls",
}


async def test_migrations_create_schema_and_enable_wal(tmp_path: Path) -> None:
    engine, _ = await open_database(f"sqlite+aiosqlite:///{tmp_path / 'schema.db'}")
    try:
        async with engine.connect() as connection:
            tables = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
            journal_mode = await connection.scalar(text("PRAGMA journal_mode"))
            version = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        await engine.dispose()
    assert tables >= EXPECTED_TABLES
    assert journal_mode == "wal"
    assert version == "0003"


async def test_migrations_are_idempotent(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'twice.db'}"
    for _ in range(2):
        engine, _ = await open_database(database_url)
        await engine.dispose()


def test_default_database_lives_in_data_folder(tmp_path: Path) -> None:
    settings = WolfSettings(data_dir=tmp_path / "data")
    assert settings.resolved_database_url().endswith("/data/seowolf.db")
    assert (tmp_path / "data").is_dir()


def test_url_keys_are_stable_and_short() -> None:
    assert url_key("https://example.com/") == url_key("https://example.com/")
    assert len(url_key("https://example.com/" + "a" * 5000)) == 40
