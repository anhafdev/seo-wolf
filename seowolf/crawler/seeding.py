from yarl import URL

from seowolf.crawler.crawl_records import PAGE_KIND, DiscoveredUrl
from seowolf.crawler.crawl_writer import CrawlWriter
from seowolf.crawler.fetcher import PageFetcher
from seowolf.crawler.frontier import CrawlFrontier
from seowolf.crawler.options import CrawlOptions
from seowolf.crawler.robots_cache import RobotsCache
from seowolf.crawler.sitemaps import SitemapCollector, SitemapEntry, default_sitemap_url
from seowolf.crawler.url_rules import UrlPolicy, UrlScope, normalise_text

__author__ = "@anhafxd"


class CrawlSeeder:
    def __init__(
        self,
        options: CrawlOptions,
        fetcher: PageFetcher,
        robots: RobotsCache,
        frontier: CrawlFrontier,
        writer: CrawlWriter,
    ) -> None:
        self.options = options
        self.fetcher = fetcher
        self.robots = robots
        self.frontier = frontier
        self.writer = writer
        self.policy = UrlPolicy.from_options(options)
        self.scope = UrlScope(options)

    def page_seed(self, raw_url: str, source: str | None) -> DiscoveredUrl | None:
        normalised = normalise_text(raw_url, self.policy)
        if normalised is None:
            return None
        return DiscoveredUrl(normalised, raw_url, PAGE_KIND, 0, source)

    def starting_seeds(self) -> list[DiscoveredUrl]:
        listed = self.options.list_mode
        raw_urls = self.options.url_list if listed else [self.options.start_url]
        seeds = [self.page_seed(raw_url, "seed") for raw_url in raw_urls]
        return [seed for seed in seeds if seed is not None]

    async def sitemap_locations(self) -> list[str]:
        locations = list(self.options.sitemap_urls)
        if self.options.list_mode or not self.options.use_robots_sitemaps:
            return locations
        policy = await self.robots.policy_for(URL(self.options.start_url))
        locations.extend(policy.sitemaps)
        if not locations:
            locations.append(default_sitemap_url(self.options.start_url))
        return list(dict.fromkeys(locations))

    def sitemap_seed(self, sitemap_url: str, entry: SitemapEntry) -> DiscoveredUrl | None:
        seed = self.page_seed(entry.loc, f"sitemap:{sitemap_url}")
        if seed is None:
            return None
        if self.options.list_mode:
            return seed
        return seed if self.scope.should_crawl(URL(seed.url), seed.url) else None

    async def seed(self) -> int:
        seeds = self.starting_seeds()
        locations = await self.sitemap_locations()
        collector = SitemapCollector(self.fetcher, max_urls=self.options.max_urls * 2)
        entries = await collector.collect(locations) if locations else []
        normalised_entries = [
            (sitemap_url, entry, normalise_text(entry.loc, self.policy))
            for sitemap_url, entry in entries
        ]
        await self.writer.save_sitemaps(collector.reports, normalised_entries)
        for sitemap_url, entry in entries:
            seed = self.sitemap_seed(sitemap_url, entry)
            if seed is not None:
                seeds.append(seed)
        return await self.frontier.seed(seeds)
