from yarl import URL

from seowolf.crawler.crawl_records import (
    PAGE_KIND,
    CrawlOutcome,
    DiscoveredUrl,
    PageRecord,
    ResourceRecord,
)
from seowolf.crawler.fetch_result import FetchResult, HopResponse
from seowolf.crawler.fetcher import PageFetcher
from seowolf.crawler.frontier import CrawlFrontier, FrontierItem
from seowolf.crawler.options import CrawlOptions
from seowolf.crawler.page_records import (
    blocked_page_record,
    content_page_record,
    redirect_page_record,
)
from seowolf.crawler.robots_cache import RobotsCache
from seowolf.crawler.url_rules import UrlPolicy, UrlScope, normalise_url
from seowolf.parsing.head_tags import robots_directives
from seowolf.parsing.page_parser import ParsedPage

__author__ = "@anhafxd"


class PageWorker:
    def __init__(
        self,
        options: CrawlOptions,
        fetcher: PageFetcher,
        robots: RobotsCache,
        frontier: CrawlFrontier,
    ) -> None:
        self.options = options
        self.fetcher = fetcher
        self.robots = robots
        self.frontier = frontier
        self.scope = UrlScope(options)
        self.policy = UrlPolicy.from_options(options)
        self.html_limit = options.max_html_bytes if options.store_html else None

    async def process(self, item: FrontierItem) -> CrawlOutcome:
        if item.kind == PAGE_KIND:
            return await self.process_page(item)
        return await self.process_status_only(item)

    async def process_page(self, item: FrontierItem) -> CrawlOutcome:
        outcome = CrawlOutcome(frontier_id=item.id)
        if not await self.robots.allows(URL(item.url)):
            outcome.pages.append(blocked_page_record(item.url, item.depth))
            return outcome
        result = await self.fetcher.fetch(item.url, may_follow=self.robots.allows)
        if not result.was_redirected:
            self.add_content_page(outcome, item.url, item.depth, result.final, result.final_is_html)
            return outcome
        outcome.pages.append(redirect_page_record(item.url, item.depth, result))
        self.add_redirect_target(outcome, item, result)
        return outcome

    def add_redirect_target(
        self, outcome: CrawlOutcome, item: FrontierItem, result: FetchResult
    ) -> None:
        if self.options.list_mode or result.chain_error or result.final.error:
            return
        target_url = result.final_url
        parsed_target = URL(target_url)
        if not self.scope.should_crawl(parsed_target, target_url):
            return
        if not self.frontier.reserve(target_url, PAGE_KIND):
            return
        outcome.completed.append(
            DiscoveredUrl(target_url, target_url, PAGE_KIND, item.depth, f"redirect:{item.url}")
        )
        self.add_content_page(outcome, target_url, item.depth, result.final, result.final_is_html)

    def add_content_page(
        self, outcome: CrawlOutcome, url: str, depth: int, hop: HopResponse, is_html: bool
    ) -> None:
        record, parsed = content_page_record(
            url, depth, hop, is_html, self.scope, self.policy, self.html_limit
        )
        outcome.pages.append(record)
        if parsed is not None:
            outcome.discovered.extend(self.discover(record, parsed))

    def discover(self, record: PageRecord, parsed: ParsedPage) -> list[DiscoveredUrl]:
        directives = robots_directives(parsed.head.robots_meta, record.x_robots_tag)
        follow_links = "nofollow" not in directives and not self.options.list_mode
        found: list[DiscoveredUrl] = []
        for link in parsed.links:
            if link.url is None or (link.nofollow and not self.options.follow_nofollow):
                continue
            target = normalise_url(link.url, self.policy)
            kind = self.link_kind(link.url, target, record.depth + 1, follow_links)
            if kind is not None and self.frontier.reserve(target, kind):
                found.append(DiscoveredUrl(target, link.href, kind, record.depth + 1, record.url))
        if not self.options.check_resources:
            return found
        for resource in parsed.resources:
            if resource.url is None:
                continue
            target = normalise_url(resource.url, self.policy)
            if self.frontier.reserve(target, resource.element):
                found.append(
                    DiscoveredUrl(target, resource.href, resource.element, record.depth, record.url)
                )
        return found

    def link_kind(self, url: URL, target: str, depth: int, follow_links: bool) -> str | None:
        if self.scope.is_internal(url):
            if not follow_links or not self.scope.passes_filters(target):
                return None
            within_depth = self.options.max_depth is None or depth <= self.options.max_depth
            return PAGE_KIND if within_depth else None
        return "external" if self.options.check_external_links else None

    async def process_status_only(self, item: FrontierItem) -> CrawlOutcome:
        outcome = CrawlOutcome(frontier_id=item.id)
        parsed_url = URL(item.url)
        resource = ResourceRecord(
            url=item.url,
            kind=item.kind,
            final_url=item.url,
            is_internal=self.scope.is_internal(parsed_url),
        )
        outcome.resource = resource
        if not await self.robots.allows(parsed_url):
            resource.error = "blocked_by_robots"
            return outcome
        result = await self.fetcher.check_status(item.url, may_follow=self.robots.allows)
        final = result.final
        resource.status_code = result.first.status_code
        resource.final_status_code = final.status_code
        resource.final_url = result.final_url
        resource.content_type = final.content_type
        resource.response_ms = result.first.response_ms
        resource.error = result.error
        resource.bytes = resource_size(final.headers)
        return outcome


def resource_size(headers: dict[str, str]) -> int | None:
    total = headers.get("content-range", "").rpartition("/")[2].strip()
    if total.isdigit():
        return int(total)
    length = headers.get("content-length", "").strip()
    return int(length) if length.isdigit() else None
