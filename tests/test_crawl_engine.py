from sqlalchemy import func, select

from seowolf.storage.models_crawls import Crawl, RobotsFile
from seowolf.storage.models_pages import Link, Redirect
from seowolf.storage.models_resources import Resource, SitemapFile, SitemapUrl
from tests.conftest import Sessions, pages_by_path, run_fixture_crawl
from tests.fixture_server import FixtureSite

__author__ = "@anhafxd"

EXPECTED_PAGES = {
    "/",
    "/about.html",
    "/blog",
    "/blog/",
    "/blog/post-one.html",
    "/blog/post-two.html",
    "/chain-start",
    "/contact.html",
    "/loop-a",
    "/old-page",
    "/orphan.html",
    "/private/secret.html",
    "/server-error",
}


async def test_full_crawl_records_every_reachable_page(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    crawl_id, status = await run_fixture_crawl(sessions, fixture_site)
    pages = await pages_by_path(sessions, fixture_site, crawl_id)
    assert status == "done"
    assert set(pages) == EXPECTED_PAGES
    assert pages["/"].title == "Wolf Outfitters | Home"
    assert pages["/"].indexable
    assert pages["/contact.html"].status_code == 404
    assert pages["/server-error"].indexability_reason == "server_error"
    assert pages["/blog/post-one.html"].indexability_reason == "noindex"
    assert pages["/blog/post-two.html"].indexability_reason == "canonicalised"
    assert pages["/private/secret.html"].fetch_error == "blocked_by_robots"
    assert pages["/old-page"].status_code == 301
    assert pages["/old-page"].final_url == fixture_site.url("/about.html")


async def test_nofollow_targets_are_not_crawled(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    crawl_id, _ = await run_fixture_crawl(sessions, fixture_site)
    assert "/nofollow-target.html" not in await pages_by_path(sessions, fixture_site, crawl_id)
    followed_id, _ = await run_fixture_crawl(sessions, fixture_site, follow_nofollow=True)
    assert "/nofollow-target.html" in await pages_by_path(sessions, fixture_site, followed_id)


async def test_redirect_chains_and_loops_are_stored(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    crawl_id, _ = await run_fixture_crawl(sessions, fixture_site)
    async with sessions() as session:
        redirects = (
            await session.scalars(select(Redirect).where(Redirect.crawl_id == crawl_id))
        ).all()
    by_source = {item.source_url.removeprefix(fixture_site.origin): item for item in redirects}
    assert by_source["/chain-start"].hop_count == 2
    assert [hop["status_code"] for hop in by_source["/chain-start"].chain] == [301, 302, 200]
    assert by_source["/loop-a"].is_loop
    assert by_source["/blog"].final_status_code == 200


async def test_resources_external_links_and_sitemaps_are_checked(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    crawl_id, _ = await run_fixture_crawl(sessions, fixture_site)
    async with sessions() as session:
        resources = (
            await session.scalars(select(Resource).where(Resource.crawl_id == crawl_id))
        ).all()
        sitemap_files = await session.scalar(
            select(func.count()).select_from(SitemapFile).where(SitemapFile.crawl_id == crawl_id)
        )
        sitemap_urls = await session.scalar(
            select(func.count()).select_from(SitemapUrl).where(SitemapUrl.crawl_id == crawl_id)
        )
        robots_rows = await session.scalar(
            select(func.count()).select_from(RobotsFile).where(RobotsFile.crawl_id == crawl_id)
        )
        image_alts = (
            await session.scalars(
                select(Link.anchor_text).where(Link.crawl_id == crawl_id, Link.element == "image")
            )
        ).all()
    statuses = {item.url.rsplit("/", 1)[-1]: item.final_status_code for item in resources}
    assert statuses["missing.png"] == 404
    assert statuses["logo.png"] == 200
    assert statuses["style.css"] == 200 and statuses["app.js"] == 200
    assert statuses["external.html"] == 200
    assert sitemap_files == 2 and sitemap_urls == 4
    assert robots_rows == 2
    assert "" in image_alts and "Wolf Outfitters logo" in image_alts


async def test_max_urls_caps_the_crawl(sessions: Sessions, fixture_site: FixtureSite) -> None:
    crawl_id, status = await run_fixture_crawl(sessions, fixture_site, max_urls=3)
    assert status == "done"
    assert len(await pages_by_path(sessions, fixture_site, crawl_id)) <= 3


async def test_max_depth_limits_discovery(sessions: Sessions, fixture_site: FixtureSite) -> None:
    crawl_id, _ = await run_fixture_crawl(
        sessions, fixture_site, max_depth=1, use_robots_sitemaps=False
    )
    pages = await pages_by_path(sessions, fixture_site, crawl_id)
    assert "/blog/" in pages
    assert "/blog/post-one.html" not in pages


async def test_list_mode_audits_only_listed_urls(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    listed = [fixture_site.url("/about.html"), fixture_site.url("/old-page")]
    crawl_id, _ = await run_fixture_crawl(sessions, fixture_site, list_mode=True, url_list=listed)
    assert set(await pages_by_path(sessions, fixture_site, crawl_id)) == {
        "/about.html",
        "/old-page",
    }


async def test_ignoring_robots_reaches_disallowed_pages(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    crawl_id, _ = await run_fixture_crawl(sessions, fixture_site, respect_robots=False)
    pages = await pages_by_path(sessions, fixture_site, crawl_id)
    assert pages["/private/secret.html"].status_code == 200


async def test_private_targets_are_blocked_without_opt_in(
    sessions: Sessions, fixture_site: FixtureSite
) -> None:
    crawl_id, status = await run_fixture_crawl(
        sessions, fixture_site, allow_private_networks=False, max_retries=0
    )
    pages = await pages_by_path(sessions, fixture_site, crawl_id)
    async with sessions() as session:
        crawl = await session.get(Crawl, crawl_id)
    assert status == "done"
    assert pages["/"].fetch_error == "blocked_private_network"
    assert crawl is not None and crawl.totals["pages_done"] == 1
