import asyncio
import contextlib
from collections.abc import Callable

from seowolf.crawler.crawl_records import CrawlOutcome
from seowolf.crawler.crawl_writer import CrawlWriter
from seowolf.crawler.frontier import CrawlFrontier, FrontierItem
from seowolf.crawler.page_worker import PageWorker

__author__ = "@anhafxd"

WRITE_BATCH_SIZE = 50
SavedCallback = Callable[[list[CrawlOutcome]], None]


class CrawlPipeline:
    def __init__(
        self,
        frontier: CrawlFrontier,
        worker: PageWorker,
        writer: CrawlWriter,
        concurrency: int,
        stop_requested: asyncio.Event,
        on_saved: SavedCallback,
    ) -> None:
        self.frontier = frontier
        self.worker = worker
        self.writer = writer
        self.concurrency = concurrency
        self.stop_requested = stop_requested
        self.on_saved = on_saved
        self.work_queue: asyncio.Queue[FrontierItem | None] = asyncio.Queue()
        self.result_queue: asyncio.Queue[CrawlOutcome | None] = asyncio.Queue()
        self.in_flight = 0
        self.progress_made = asyncio.Event()
        self.failure: BaseException | None = None

    async def run(self) -> None:
        workers = [asyncio.create_task(self.work_loop()) for _ in range(self.concurrency)]
        writer_task = asyncio.create_task(self.write_loop())
        try:
            await self.feed_loop()
        finally:
            for _ in workers:
                self.work_queue.put_nowait(None)
            await asyncio.gather(*workers, return_exceptions=True)
            self.result_queue.put_nowait(None)
            await writer_task

    async def feed_loop(self) -> None:
        while not self.stop_requested.is_set():
            self.progress_made.clear()
            if self.work_queue.qsize() < self.concurrency * 2:
                batch = await self.frontier.claim_batch(self.concurrency * 4)
                for item in batch:
                    self.work_queue.put_nowait(item)
                self.in_flight += len(batch)
                if not batch and self.in_flight == 0:
                    return
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.progress_made.wait(), timeout=0.5)

    async def work_loop(self) -> None:
        while True:
            item = await self.work_queue.get()
            if item is None:
                return
            if self.stop_requested.is_set():
                continue
            await self.result_queue.put(await self.safe_process(item))

    async def safe_process(self, item: FrontierItem) -> CrawlOutcome:
        try:
            return await self.worker.process(item)
        except Exception as problem:
            return CrawlOutcome(frontier_id=item.id, state="failed", error=repr(problem))

    async def write_loop(self) -> None:
        finished = False
        while not finished:
            first = await self.result_queue.get()
            if first is None:
                return
            batch = [first]
            while len(batch) < WRITE_BATCH_SIZE and not self.result_queue.empty():
                following = self.result_queue.get_nowait()
                if following is None:
                    finished = True
                    break
                batch.append(following)
            await self.persist(batch)

    async def persist(self, batch: list[CrawlOutcome]) -> None:
        try:
            await self.writer.save_outcomes(batch)
        except Exception as problem:
            self.failure = problem
            self.stop_requested.set()
            raise
        finally:
            self.in_flight -= len(batch)
            self.progress_made.set()
        self.on_saved(batch)
