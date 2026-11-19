from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from seowolf.crawler.engine import CrawlEngine
from seowolf.crawler.options import CrawlOptions
from seowolf.storage.database import open_database
from seowolf.storage.models_pages import Page
from seowolf.storage.repositories_crawls import create_crawl
from seowolf.storage.repositories_projects import find_or_create_project
from tests.fixture_server import FixtureSite, serve_fixture_site

__author__ = "@anhafxd"

Sessions = async_sessionmaker[AsyncSession]


@pytest.fixture
def fixture_site() -> Iterator[FixtureSite]:
    with serve_fixture_site() as site:
        yield site


@pytest.fixture
async def sessions(tmp_path: Path) -> AsyncIterator[Sessions]:
    engine, session_factory = await open_database(f"sqlite+aiosqlite:///{tmp_path / 'wolf.db'}")
    yield session_factory
    await engine.dispose()


def fixture_options(site: FixtureSite, **changes: object) -> CrawlOptions:
    values: dict[str, object] = {
        "start_url": site.url("/"),
        "allow_private_networks": True,
        "per_host_delay": 0,
    }
    values.update(changes)
    return CrawlOptions.model_validate(values)


async def create_test_crawl(sessions: Sessions, options: CrawlOptions) -> int:
    async with sessions() as session, session.begin():
        project = await find_or_create_project(session, "fixture", options.start_url)
        crawl = await create_crawl(session, project, options)
        return crawl.id


async def run_fixture_crawl(
    sessions: Sessions, site: FixtureSite, **changes: object
) -> tuple[int, str]:
    options = fixture_options(site, **changes)
    crawl_id = await create_test_crawl(sessions, options)
    status = await CrawlEngine(sessions, crawl_id, options).run()
    return crawl_id, status


async def pages_by_path(sessions: Sessions, site: FixtureSite, crawl_id: int) -> dict[str, Page]:
    async with sessions() as session:
        pages = (await session.scalars(select(Page).where(Page.crawl_id == crawl_id))).all()
    return {page.url.removeprefix(site.origin): page for page in pages}
