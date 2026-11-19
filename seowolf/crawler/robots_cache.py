import asyncio

from yarl import URL

from seowolf.crawler.fetcher import PageFetcher
from seowolf.crawler.politeness import HostThrottle
from seowolf.crawler.robots import MAX_ROBOTS_BYTES, RobotsPolicy, policy_from_response

__author__ = "@anhafxd"


def origin_of(url: URL) -> str:
    return str(url.origin())


class RobotsCache:
    def __init__(self, fetcher: PageFetcher, throttle: HostThrottle, respect_robots: bool) -> None:
        self.fetcher = fetcher
        self.throttle = throttle
        self.respect_robots = respect_robots
        self.policies: dict[str, RobotsPolicy] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    async def policy_for(self, url: URL) -> RobotsPolicy:
        origin = origin_of(url)
        if origin in self.policies:
            return self.policies[origin]
        lock = self.locks.setdefault(origin, asyncio.Lock())
        async with lock:
            if origin not in self.policies:
                self.policies[origin] = await self.download_policy(origin, url.host or "")
        return self.policies[origin]

    async def download_policy(self, origin: str, host: str) -> RobotsPolicy:
        result = await self.fetcher.fetch(
            f"{origin}/robots.txt", read_any_body=True, max_bytes=MAX_ROBOTS_BYTES
        )
        if result.error == "blocked_private_network":
            return RobotsPolicy(blanket_allow=True)
        status_code = None if result.error else result.final.status_code
        body = result.final.body if result.hops else b""
        policy = policy_from_response(status_code, body)
        if self.respect_robots:
            self.throttle.apply_crawl_delay(host, policy.crawl_delay())
        return policy

    async def allows(self, url: URL) -> bool:
        if not self.respect_robots:
            return True
        policy = await self.policy_for(url)
        return policy.is_allowed(url)

    def snapshots(self) -> list[dict[str, object]]:
        return [
            {
                "origin": origin,
                "status_code": policy.status_code,
                "body": policy.body,
                "sitemaps": policy.sitemaps,
                "blanket_allow": policy.blanket_allow,
            }
            for origin, policy in self.policies.items()
        ]
