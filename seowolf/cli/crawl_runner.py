import asyncio
import signal
from collections.abc import Callable
from types import FrameType

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from yarl import URL

from seowolf.crawler.engine import CrawlEngine, CrawlProgress
from seowolf.crawler.options import CrawlOptions
from seowolf.settings import WolfSettings
from seowolf.storage.database import open_database
from seowolf.storage.repositories_crawls import create_crawl, find_crawl
from seowolf.storage.repositories_pages import CrawlSummary, build_crawl_summary
from seowolf.storage.repositories_projects import find_or_create_project

__author__ = "@anhafxd"


class CrawlNotFoundError(Exception):
    def __init__(self, crawl_id: int) -> None:
        super().__init__(f"crawl {crawl_id} does not exist")
        self.crawl_id = crawl_id


def install_pause_handler(engine: CrawlEngine, console: Console) -> Callable[[], None]:
    loop = asyncio.get_running_loop()
    previous_handler = signal.getsignal(signal.SIGINT)

    def pause_on_first_interrupt(signal_number: int, frame: FrameType | None) -> None:
        console.print("[yellow]Pausing after in-flight requests… press Ctrl+C again to abort.")
        signal.signal(signal.SIGINT, signal.default_int_handler)
        loop.call_soon_threadsafe(engine.request_stop)

    signal.signal(signal.SIGINT, pause_on_first_interrupt)
    return lambda: signal.signal(signal.SIGINT, previous_handler)


def build_progress(console: Console) -> Progress:
    return Progress(
        SpinnerColumn(style="red"),
        TextColumn("[bold]{task.description}"),
        BarColumn(complete_style="red", finished_style="blue"),
        MofNCompleteColumn(),
        TextColumn("{task.fields[detail]}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


async def run_engine(
    sessions: async_sessionmaker[AsyncSession],
    crawl_id: int,
    options: CrawlOptions,
    console: Console,
) -> str:
    with build_progress(console) as progress:
        task = progress.add_task("Crawling", total=None, detail="")

        def show(state: CrawlProgress) -> None:
            done = state.pages_done + state.resources_done + state.failed
            found = state.pages_found + state.resources_found
            detail = f"pages {state.pages_done}/{state.pages_found} · checks {state.resources_done}"
            progress.update(task, completed=done, total=max(found, done), detail=detail)

        engine = CrawlEngine(sessions, crawl_id, options, on_progress=show)
        restore_handler = install_pause_handler(engine, console)
        try:
            return await engine.run()
        finally:
            restore_handler()


async def start_crawl(
    settings: WolfSettings, project_name: str | None, options: CrawlOptions, console: Console
) -> tuple[int, str, CrawlSummary]:
    engine, sessions = await open_database(settings.resolved_database_url())
    try:
        name = project_name or URL(options.start_url).host or "default"
        async with sessions() as session, session.begin():
            project = await find_or_create_project(session, name, options.start_url)
            crawl = await create_crawl(session, project, options)
            crawl_id = crawl.id
        console.print(f"[bold red]SEO Wolf[/] crawl [bold]#{crawl_id}[/] · project [bold]{name}[/]")
        status = await run_engine(sessions, crawl_id, options, console)
        async with sessions() as session:
            summary = await build_crawl_summary(session, crawl_id)
        return crawl_id, status, summary
    finally:
        await engine.dispose()


async def resume_crawl(
    settings: WolfSettings, crawl_id: int, console: Console
) -> tuple[int, str, CrawlSummary]:
    engine, sessions = await open_database(settings.resolved_database_url())
    try:
        async with sessions() as session:
            crawl = await find_crawl(session, crawl_id)
        if crawl is None:
            raise CrawlNotFoundError(crawl_id)
        options = CrawlOptions.model_validate(crawl.settings_snapshot)
        console.print(f"[bold red]SEO Wolf[/] resuming crawl [bold]#{crawl_id}[/]")
        status = await run_engine(sessions, crawl_id, options, console)
        async with sessions() as session:
            summary = await build_crawl_summary(session, crawl_id)
        return crawl_id, status, summary
    finally:
        await engine.dispose()


async def load_summary(settings: WolfSettings, crawl_id: int) -> CrawlSummary:
    engine, sessions = await open_database(settings.resolved_database_url())
    try:
        async with sessions() as session:
            if await find_crawl(session, crawl_id) is None:
                raise CrawlNotFoundError(crawl_id)
            return await build_crawl_summary(session, crawl_id)
    finally:
        await engine.dispose()
