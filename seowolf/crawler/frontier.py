from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from seowolf.crawler.crawl_records import PAGE_KIND, DiscoveredUrl
from seowolf.storage.bulk_insert import add_rows_skipping_duplicates
from seowolf.storage.models_base import url_key
from seowolf.storage.models_crawls import FrontierEntry

__author__ = "@anhafxd"


@dataclass(frozen=True)
class FrontierItem:
    id: int
    url: str
    kind: str
    depth: int


def frontier_row(crawl_id: int, discovered: DiscoveredUrl, state: str) -> dict[str, object]:
    return {
        "crawl_id": crawl_id,
        "url": discovered.url,
        "url_key": url_key(discovered.url),
        "original_url": discovered.original_url,
        "kind": discovered.kind,
        "depth": discovered.depth,
        "priority": discovered.depth,
        "state": state,
        "attempts": 0,
        "discovered_from": discovered.discovered_from,
    }


class CrawlFrontier:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        crawl_id: int,
        max_pages: int,
        max_resources: int,
    ) -> None:
        self.session_factory = session_factory
        self.crawl_id = crawl_id
        self.max_pages = max_pages
        self.max_resources = max_resources
        self.seen_urls: set[str] = set()
        self.page_count = 0
        self.resource_count = 0

    async def load(self) -> None:
        statement = select(FrontierEntry.url, FrontierEntry.kind).where(
            FrontierEntry.crawl_id == self.crawl_id
        )
        async with self.session_factory() as session:
            for url, kind in (await session.execute(statement)).all():
                self.remember(url, kind)

    def remember(self, url: str, kind: str) -> None:
        self.seen_urls.add(url)
        if kind == PAGE_KIND:
            self.page_count += 1
        else:
            self.resource_count += 1

    @property
    def is_empty(self) -> bool:
        return not self.seen_urls

    def has_room_for(self, kind: str) -> bool:
        if kind == PAGE_KIND:
            return self.page_count < self.max_pages
        return self.resource_count < self.max_resources

    def reserve(self, url: str, kind: str) -> bool:
        if url in self.seen_urls or not self.has_room_for(kind):
            return False
        self.remember(url, kind)
        return True

    async def seed(self, discovered: list[DiscoveredUrl]) -> int:
        fresh = [item for item in discovered if self.reserve(item.url, item.kind)]
        async with self.session_factory() as session, session.begin():
            rows = [frontier_row(self.crawl_id, item, "queued") for item in fresh]
            await add_rows_skipping_duplicates(session, FrontierEntry, rows)
        return len(fresh)

    async def claim_batch(self, limit: int) -> list[FrontierItem]:
        statement = (
            select(FrontierEntry.id, FrontierEntry.url, FrontierEntry.kind, FrontierEntry.depth)
            .where(FrontierEntry.crawl_id == self.crawl_id, FrontierEntry.state == "queued")
            .order_by(FrontierEntry.priority, FrontierEntry.id)
            .limit(limit)
        )
        async with self.session_factory() as session, session.begin():
            rows = (await session.execute(statement)).all()
            if rows:
                await session.execute(
                    update(FrontierEntry)
                    .where(FrontierEntry.id.in_([row.id for row in rows]))
                    .values(state="in_progress", attempts=FrontierEntry.attempts + 1)
                )
        return [FrontierItem(row.id, row.url, row.kind, row.depth) for row in rows]

    async def requeue_interrupted(self) -> int:
        statement = (
            update(FrontierEntry)
            .where(FrontierEntry.crawl_id == self.crawl_id, FrontierEntry.state == "in_progress")
            .values(state="queued")
        )
        async with self.session_factory() as session, session.begin():
            result = await session.execute(statement)
        return result.rowcount or 0

    async def count_by_kind_and_state(self) -> dict[tuple[str, str], int]:
        statement = (
            select(FrontierEntry.kind, FrontierEntry.state, func.count())
            .where(FrontierEntry.crawl_id == self.crawl_id)
            .group_by(FrontierEntry.kind, FrontierEntry.state)
        )
        async with self.session_factory() as session:
            rows = (await session.execute(statement)).all()
        return {(kind, state): count for kind, state, count in rows}
