from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from seowolf.storage.models_pages import Link, Page, Redirect
from seowolf.storage.models_resources import Resource, SitemapFile, SitemapUrl

__author__ = "@anhafxd"


@dataclass
class CrawlSummary:
    page_total: int = 0
    status_counts: list[tuple[int | None, int]] = field(default_factory=list)
    indexability_counts: list[tuple[str, int]] = field(default_factory=list)
    broken_links: list[tuple[str, str, int | None]] = field(default_factory=list)
    broken_resources: list[tuple[str, str, int | None, str | None]] = field(default_factory=list)
    redirect_count: int = 0
    redirect_loops: int = 0
    long_chains: int = 0
    slowest_pages: list[tuple[str, int]] = field(default_factory=list)
    sitemap_files: int = 0
    sitemap_urls: int = 0


async def grouped_counts(
    session: AsyncSession, column: Any, crawl_id: int
) -> list[tuple[Any, int]]:
    statement = (
        select(column, func.count())
        .where(Page.crawl_id == crawl_id)
        .group_by(column)
        .order_by(func.count().desc())
    )
    return [tuple(row) for row in (await session.execute(statement)).all()]


async def broken_internal_links(
    session: AsyncSession, crawl_id: int, limit: int
) -> list[tuple[str, str, int | None]]:
    source_page = aliased(Page)
    target_page = aliased(Page)
    statement = (
        select(source_page.url, target_page.url, target_page.status_code)
        .select_from(Link)
        .join(source_page, source_page.id == Link.from_page_id)
        .join(
            target_page,
            and_(target_page.crawl_id == Link.crawl_id, target_page.url_key == Link.to_url_key),
        )
        .where(
            Link.crawl_id == crawl_id,
            Link.element.in_(["a", "area"]),
            or_(target_page.status_code >= 400, target_page.fetch_error.in_(["timeout"])),
        )
        .order_by(target_page.status_code.desc(), source_page.url)
        .limit(limit)
    )
    return [tuple(row) for row in (await session.execute(statement)).all()]


async def broken_resources(
    session: AsyncSession, crawl_id: int, limit: int
) -> list[tuple[str, str, int | None, str | None]]:
    statement = (
        select(Resource.kind, Resource.url, Resource.final_status_code, Resource.error)
        .where(
            Resource.crawl_id == crawl_id,
            or_(
                Resource.final_status_code >= 400,
                and_(Resource.error.is_not(None), Resource.error != "blocked_by_robots"),
            ),
        )
        .order_by(Resource.kind, Resource.url)
        .limit(limit)
    )
    return [tuple(row) for row in (await session.execute(statement)).all()]


async def count_where(session: AsyncSession, *conditions: Any, model: type[Any] = Redirect) -> int:
    statement = select(func.count()).select_from(model).where(*conditions)
    return int(await session.scalar(statement) or 0)


async def build_crawl_summary(
    session: AsyncSession, crawl_id: int, limit: int = 10
) -> CrawlSummary:
    summary = CrawlSummary()
    summary.page_total = await count_where(session, Page.crawl_id == crawl_id, model=Page)
    summary.status_counts = await grouped_counts(session, Page.status_code, crawl_id)
    summary.indexability_counts = await grouped_counts(session, Page.indexability_reason, crawl_id)
    summary.broken_links = await broken_internal_links(session, crawl_id, limit)
    summary.broken_resources = await broken_resources(session, crawl_id, limit)
    summary.redirect_count = await count_where(session, Redirect.crawl_id == crawl_id)
    summary.redirect_loops = await count_where(
        session, Redirect.crawl_id == crawl_id, Redirect.is_loop.is_(True)
    )
    summary.long_chains = await count_where(
        session, Redirect.crawl_id == crawl_id, Redirect.hop_count > 1
    )
    slowest = (
        select(Page.url, Page.response_ms)
        .where(Page.crawl_id == crawl_id, Page.response_ms.is_not(None))
        .order_by(Page.response_ms.desc())
        .limit(5)
    )
    summary.slowest_pages = [tuple(row) for row in (await session.execute(slowest)).all()]
    summary.sitemap_files = await count_where(
        session, SitemapFile.crawl_id == crawl_id, model=SitemapFile
    )
    summary.sitemap_urls = await count_where(
        session, SitemapUrl.crawl_id == crawl_id, model=SitemapUrl
    )
    return summary
