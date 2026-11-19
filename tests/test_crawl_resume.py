from sqlalchemy import func, select

from seowolf.crawler.engine import CrawlEngine, CrawlProgress
from seowolf.storage.models_crawls import Crawl, FrontierEntry
from seowolf.storage.models_pages import Page
from tests.conftest import Sessions, create_test_crawl, fixture_options, pages_by_path
from tests.fixture_server import FixtureSite
from tests.test_crawl_engine import EXPECTED_PAGES

__author__ = "@anhafxd"


async def test_paused_crawl_resumes_without_duplicates(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    options = fixture_options(fixture_site, concurrency=1)
    crawl_id = await create_test_crawl(sessions, options)
    engine = CrawlEngine(sessions, crawl_id, options)

    def stop_after_first_page(progress: CrawlProgress) -> None:
        if progress.pages_done >= 1:
            engine.request_stop()

    engine.on_progress = stop_after_first_page
    assert await engine.run() == "paused"
    partial = await pages_by_path(sessions, fixture_site, crawl_id)
    assert 1 <= len(partial) < len(EXPECTED_PAGES)

    assert await CrawlEngine(sessions, crawl_id, options).run() == "done"
    async with sessions() as session:
        page_rows = await session.scalar(
            select(func.count()).select_from(Page).where(Page.crawl_id == crawl_id)
        )
        unfinished = await session.scalar(
            select(func.count())
            .select_from(FrontierEntry)
            .where(FrontierEntry.crawl_id == crawl_id, FrontierEntry.state != "done")
        )
        crawl = await session.get(Crawl, crawl_id)
    assert page_rows == len(EXPECTED_PAGES)
    assert unfinished == 0
    assert crawl is not None and crawl.status == "done" and crawl.finished_at is not None


async def test_interrupted_entries_are_requeued(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    options = fixture_options(fixture_site)
    crawl_id = await create_test_crawl(sessions, options)
    engine = CrawlEngine(sessions, crawl_id, options)
    engine.request_stop()
    assert await engine.run() in {"paused", "done"}
    async with sessions() as session, session.begin():
        entries = (
            await session.scalars(select(FrontierEntry).where(FrontierEntry.crawl_id == crawl_id))
        ).all()
        for entry in entries:
            entry.state = "in_progress"
    assert await CrawlEngine(sessions, crawl_id, options).run() == "done"
    assert set(await pages_by_path(sessions, fixture_site, crawl_id)) == EXPECTED_PAGES
