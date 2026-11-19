from dataclasses import asdict
from typing import Any

from sqlalchemy import case, delete, insert, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from seowolf.crawler.crawl_records import CrawlOutcome, PageRecord
from seowolf.crawler.frontier import frontier_row
from seowolf.crawler.sitemaps import SitemapEntry, SitemapReport
from seowolf.storage.bulk_insert import add_rows_skipping_duplicates
from seowolf.storage.models_base import url_key
from seowolf.storage.models_crawls import FrontierEntry, RobotsFile
from seowolf.storage.models_pages import Link, Page, Redirect
from seowolf.storage.models_resources import Resource, SitemapFile, SitemapUrl

__author__ = "@anhafxd"


class CrawlWriter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], crawl_id: int) -> None:
        self.session_factory = session_factory
        self.crawl_id = crawl_id

    async def save_outcomes(self, outcomes: list[CrawlOutcome]) -> None:
        async with self.session_factory() as session, session.begin():
            pages = [page for outcome in outcomes for page in outcome.pages]
            await self.save_pages(session, pages)
            resources = [
                {"crawl_id": self.crawl_id, "url_key": url_key(outcome.resource.url)}
                | asdict(outcome.resource)
                for outcome in outcomes
                if outcome.resource is not None
            ]
            await add_rows_skipping_duplicates(session, Resource, resources)
            new_entries = [
                frontier_row(self.crawl_id, item, "queued")
                for outcome in outcomes
                for item in outcome.discovered
            ]
            new_entries += [
                frontier_row(self.crawl_id, item, "done")
                for outcome in outcomes
                for item in outcome.completed
            ]
            await add_rows_skipping_duplicates(session, FrontierEntry, new_entries)
            await self.close_frontier_entries(session, outcomes)

    async def save_pages(self, session: AsyncSession, pages: list[PageRecord]) -> None:
        if not pages:
            return
        page_rows = [
            Page(crawl_id=self.crawl_id, url_key=url_key(page.url), **page.column_values())
            for page in pages
        ]
        session.add_all(page_rows)
        await session.flush()
        link_rows: list[dict[str, Any]] = []
        redirect_rows: list[dict[str, Any]] = []
        for page, page_row in zip(pages, page_rows, strict=True):
            for link in page.links:
                link_values = asdict(link)
                link_values["to_url_key"] = url_key(link.to_url) if link.to_url else None
                link_rows.append(
                    {"crawl_id": self.crawl_id, "from_page_id": page_row.id} | link_values
                )
            if page.redirect is not None:
                redirect_rows.append({"crawl_id": self.crawl_id} | asdict(page.redirect))
        if link_rows:
            await session.execute(insert(Link), link_rows)
        if redirect_rows:
            await session.execute(insert(Redirect), redirect_rows)

    async def close_frontier_entries(
        self, session: AsyncSession, outcomes: list[CrawlOutcome]
    ) -> None:
        states = {outcome.frontier_id: outcome.state for outcome in outcomes}
        if not states:
            return
        await session.execute(
            update(FrontierEntry)
            .where(FrontierEntry.id.in_(list(states)))
            .values(state=case(states, value=FrontierEntry.id, else_=FrontierEntry.state))
        )

    async def save_sitemaps(
        self, reports: list[SitemapReport], entries: list[tuple[str, SitemapEntry, str | None]]
    ) -> None:
        report_rows = [{"crawl_id": self.crawl_id} | asdict(report) for report in reports]
        entry_rows = [
            {
                "crawl_id": self.crawl_id,
                "sitemap_url": sitemap_url,
                "loc": entry.loc,
                "normalised_url": normalised,
                "url_key": url_key(normalised) if normalised else None,
                "lastmod": entry.lastmod,
            }
            for sitemap_url, entry, normalised in entries
        ]
        async with self.session_factory() as session, session.begin():
            if report_rows:
                await session.execute(insert(SitemapFile), report_rows)
            for start in range(0, len(entry_rows), 5000):
                await session.execute(insert(SitemapUrl), entry_rows[start : start + 5000])

    async def save_robots(self, snapshots: list[dict[str, Any]]) -> None:
        if not snapshots:
            return
        rows = [{"crawl_id": self.crawl_id} | snapshot for snapshot in snapshots]
        async with self.session_factory() as session, session.begin():
            origins = [snapshot["origin"] for snapshot in snapshots]
            await session.execute(
                delete(RobotsFile).where(
                    RobotsFile.crawl_id == self.crawl_id, RobotsFile.origin.in_(origins)
                )
            )
            await session.execute(insert(RobotsFile), rows)
