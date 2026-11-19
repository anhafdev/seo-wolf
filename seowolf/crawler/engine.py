import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from yarl import URL

from seowolf.crawler.crawl_records import PAGE_KIND, CrawlOutcome
from seowolf.crawler.crawl_writer import CrawlWriter
from seowolf.crawler.fetcher import PageFetcher
from seowolf.crawler.frontier import CrawlFrontier
from seowolf.crawler.options import CrawlOptions
from seowolf.crawler.page_worker import PageWorker
from seowolf.crawler.pipeline import CrawlPipeline
from seowolf.crawler.politeness import HostThrottle
from seowolf.crawler.robots_cache import RobotsCache, origin_of
from seowolf.crawler.seeding import CrawlSeeder
from seowolf.storage.repositories_crawls import finish_crawl, mark_crawl_running

__author__ = "@anhafxd"


@dataclass
class CrawlProgress:
    pages_done: int = 0
    resources_done: int = 0
    failed: int = 0
    pages_found: int = 0
    resources_found: int = 0
    started_at: float = field(default_factory=time.monotonic)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at


ProgressCallback = Callable[[CrawlProgress], None]


class CrawlEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        crawl_id: int,
        options: CrawlOptions,
        on_progress: ProgressCallback | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.crawl_id = crawl_id
        self.options = options
        self.on_progress = on_progress
        self.transport = transport
        self.stop_requested = asyncio.Event()
        self.progress = CrawlProgress()
        self.robots_status: int | None = None

    def request_stop(self) -> None:
        self.stop_requested.set()

    async def run(self) -> str:
        async with self.session_factory() as session, session.begin():
            await mark_crawl_running(session, self.crawl_id)
        throttle = HostThrottle(self.options.per_host_delay, self.options.per_host_concurrency)
        fetcher = PageFetcher(self.options, throttle, self.transport)
        robots = RobotsCache(fetcher, throttle, self.options.respect_robots)
        frontier = CrawlFrontier(
            self.session_factory, self.crawl_id, self.options.max_urls, self.options.max_resources
        )
        writer = CrawlWriter(self.session_factory, self.crawl_id)
        status, failure_reason = "done", None
        try:
            await self.crawl(fetcher, robots, frontier, writer)
            status = await self.final_status(frontier)
        except Exception as problem:
            status, failure_reason = "failed", repr(problem)
        finally:
            await writer.save_robots(robots.snapshots())
            await fetcher.close()
        totals = await self.totals(frontier, robots)
        async with self.session_factory() as session, session.begin():
            await finish_crawl(session, self.crawl_id, status, totals, failure_reason)
        return status

    async def crawl(
        self,
        fetcher: PageFetcher,
        robots: RobotsCache,
        frontier: CrawlFrontier,
        writer: CrawlWriter,
    ) -> None:
        await frontier.load()
        if frontier.is_empty:
            await CrawlSeeder(self.options, fetcher, robots, frontier, writer).seed()
        else:
            await frontier.requeue_interrupted()
        await self.load_progress(frontier)
        worker = PageWorker(self.options, fetcher, robots, frontier)
        pipeline = CrawlPipeline(
            frontier,
            worker,
            writer,
            self.options.concurrency,
            self.stop_requested,
            lambda batch: self.record_progress(batch, frontier),
        )
        await pipeline.run()
        if pipeline.failure is not None:
            raise pipeline.failure

    async def final_status(self, frontier: CrawlFrontier) -> str:
        counts = await frontier.count_by_kind_and_state()
        unfinished = sum(
            count for (_, state), count in counts.items() if state in {"queued", "in_progress"}
        )
        return "paused" if self.stop_requested.is_set() and unfinished else "done"

    async def load_progress(self, frontier: CrawlFrontier) -> None:
        counts = await frontier.count_by_kind_and_state()
        for (kind, state), count in counts.items():
            if state == "failed":
                self.progress.failed += count
            elif state == "done" and kind == PAGE_KIND:
                self.progress.pages_done += count
            elif state == "done":
                self.progress.resources_done += count
        self.sync_found(frontier)

    def sync_found(self, frontier: CrawlFrontier) -> None:
        self.progress.pages_found = frontier.page_count
        self.progress.resources_found = frontier.resource_count
        if self.on_progress is not None:
            self.on_progress(self.progress)

    def record_progress(self, batch: list[CrawlOutcome], frontier: CrawlFrontier) -> None:
        for outcome in batch:
            if outcome.state == "failed":
                self.progress.failed += 1
            elif outcome.resource is not None:
                self.progress.resources_done += 1
            else:
                self.progress.pages_done += len(outcome.pages)
        self.sync_found(frontier)

    async def totals(self, frontier: CrawlFrontier, robots: RobotsCache) -> dict[str, Any]:
        counts = await frontier.count_by_kind_and_state()
        start_origin = origin_of(URL(self.options.start_url))
        start_policy = robots.policies.get(start_origin)
        return {
            "pages_done": self.progress.pages_done,
            "resources_done": self.progress.resources_done,
            "failed": self.progress.failed,
            "frontier": {f"{kind}:{state}": count for (kind, state), count in counts.items()},
            "robots_status_code": start_policy.status_code if start_policy else None,
            "robots_blanket_allow": start_policy.blanket_allow if start_policy else None,
            "elapsed_seconds": round(self.progress.elapsed_seconds, 2),
        }
