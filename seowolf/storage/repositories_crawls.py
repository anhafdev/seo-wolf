from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seowolf.crawler.options import CrawlOptions
from seowolf.storage.models_base import utc_now
from seowolf.storage.models_crawls import Crawl
from seowolf.storage.models_projects import Project

__author__ = "@anhafxd"


async def create_crawl(session: AsyncSession, project: Project, options: CrawlOptions) -> Crawl:
    crawl = Crawl(
        project_id=project.id,
        status="queued",
        mode=options.mode,
        totals={},
        settings_snapshot=options.model_dump(mode="json"),
    )
    session.add(crawl)
    await session.flush()
    return crawl


async def find_crawl(session: AsyncSession, crawl_id: int) -> Crawl | None:
    return await session.get(Crawl, crawl_id)


async def mark_crawl_running(session: AsyncSession, crawl_id: int) -> None:
    crawl = await session.get(Crawl, crawl_id)
    if crawl is not None:
        crawl.status = "running"
        crawl.started_at = crawl.started_at or utc_now()
        crawl.failure_reason = None


async def finish_crawl(
    session: AsyncSession,
    crawl_id: int,
    status: str,
    totals: dict[str, Any],
    failure_reason: str | None = None,
) -> None:
    crawl = await session.get(Crawl, crawl_id)
    if crawl is None:
        return
    crawl.status = status
    crawl.totals = totals
    crawl.failure_reason = failure_reason
    if status in {"done", "failed"}:
        crawl.finished_at = utc_now()


async def recent_crawls(
    session: AsyncSession, project_id: int | None = None, limit: int = 20
) -> list[tuple[Crawl, Project]]:
    statement = select(Crawl, Project).join(Project, Project.id == Crawl.project_id)
    if project_id is not None:
        statement = statement.where(Crawl.project_id == project_id)
    statement = statement.order_by(Crawl.id.desc()).limit(limit)
    return [(crawl, project) for crawl, project in (await session.execute(statement)).all()]
