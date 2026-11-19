import time
from collections.abc import Awaitable, Callable

import httpx
from yarl import URL

from seowolf.crawler.fetch_result import HTML_CONTENT_TYPES, FetchResult, HopResponse
from seowolf.crawler.guarded_transport import GuardedTransport
from seowolf.crawler.network_guard import BlockedDestinationError
from seowolf.crawler.options import CrawlOptions
from seowolf.crawler.politeness import HostThrottle, parse_retry_after
from seowolf.crawler.url_rules import UrlPolicy, normalise_url, parse_web_url

__author__ = "@anhafxd"

RETRY_STATUSES = {429, 503}
RETRY_ERRORS = {"timeout", "connection_error", "protocol_error"}
ACCEPT_HEADER = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
FollowCheck = Callable[[URL], Awaitable[bool]]


def combined_headers(response: httpx.Response) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in response.headers.multi_items():
        key = name.lower()
        headers[key] = f"{headers[key]}, {value}" if key in headers else value
    return headers


def error_name(problem: Exception) -> str:
    if isinstance(problem, BlockedDestinationError):
        return "blocked_private_network"
    if isinstance(problem, httpx.TimeoutException):
        return "timeout"
    if isinstance(problem, httpx.ConnectError):
        text = str(problem).upper()
        return "tls_error" if "SSL" in text or "CERTIFICATE" in text else "connection_error"
    if isinstance(problem, httpx.RemoteProtocolError | httpx.LocalProtocolError):
        return "protocol_error"
    if isinstance(problem, httpx.UnsupportedProtocol | httpx.InvalidURL):
        return "invalid_url"
    return "http_error"


class PageFetcher:
    def __init__(
        self,
        options: CrawlOptions,
        throttle: HostThrottle,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.options = options
        self.throttle = throttle
        self.policy = UrlPolicy()
        headers = {"User-Agent": options.effective_user_agent, "Accept": ACCEPT_HEADER}
        headers.update(options.custom_headers)
        self.client = httpx.AsyncClient(
            transport=transport
            or GuardedTransport(options.allow_private_networks, options.concurrency * 4),
            headers=headers,
            timeout=httpx.Timeout(
                options.timeout_seconds, connect=min(options.timeout_seconds, 10.0)
            ),
            follow_redirects=False,
            trust_env=False,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        read_any_body: bool = False,
        max_bytes: int | None = None,
        may_follow: FollowCheck | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> FetchResult:
        result = FetchResult(requested_url=url)
        visited = {url}
        current_url, current_method = url, method
        byte_limit = max_bytes or self.options.max_body_bytes
        for hop_number in range(self.options.max_redirect_hops + 1):
            hop = await self.request_with_retries(
                current_method, current_url, read_any_body, byte_limit, extra_headers
            )
            result.hops.append(hop)
            if hop.error or not hop.is_redirect:
                return result
            target = parse_web_url(hop.location or "", URL(current_url))
            if target is None:
                result.chain_error = "invalid_redirect_location"
                return result
            target_text = normalise_url(target, self.policy)
            if target_text in visited:
                result.redirect_loop = True
                result.chain_error = "redirect_loop"
                return result
            if hop_number == self.options.max_redirect_hops:
                result.chain_error = "too_many_redirects"
                return result
            if may_follow is not None and not await may_follow(target):
                result.chain_error = "redirect_blocked_by_robots"
                return result
            visited.add(target_text)
            current_url = target_text
            if hop.status_code == 303 and current_method != "HEAD":
                current_method = "GET"
        return result

    async def check_status(self, url: str, may_follow: FollowCheck | None = None) -> FetchResult:
        result = await self.fetch(url, method="HEAD", may_follow=may_follow)
        if result.hops and result.final.status_code in {403, 405, 501}:
            return await self.fetch(
                url, may_follow=may_follow, max_bytes=1, extra_headers={"Range": "bytes=0-0"}
            )
        return result

    async def request_with_retries(
        self,
        method: str,
        url: str,
        read_any_body: bool,
        byte_limit: int,
        extra_headers: dict[str, str] | None,
    ) -> HopResponse:
        host = URL(url).host or ""
        hop = HopResponse(url=url)
        for attempt in range(self.options.max_retries + 1):
            hop = await self.single_request(method, url, read_any_body, byte_limit, extra_headers)
            should_retry = hop.status_code in RETRY_STATUSES or hop.error in RETRY_ERRORS
            if not should_retry or attempt == self.options.max_retries:
                break
            self.throttle.slow_down(host, parse_retry_after(hop.headers.get("retry-after")))
        if hop.status_code not in RETRY_STATUSES:
            self.throttle.recover(host)
        return hop

    async def single_request(
        self,
        method: str,
        url: str,
        read_any_body: bool,
        byte_limit: int,
        extra_headers: dict[str, str] | None,
    ) -> HopResponse:
        hop = HopResponse(url=url)
        async with self.throttle.slot(URL(url).host or ""):
            started = time.perf_counter()
            try:
                async with self.client.stream(method, url, headers=extra_headers) as response:
                    hop.response_ms = round((time.perf_counter() - started) * 1000)
                    hop.status_code = response.status_code
                    hop.headers = combined_headers(response)
                    hop.http_version = response.http_version
                    if method != "HEAD" and self.should_read_body(hop, read_any_body):
                        await self.read_body(response, hop, byte_limit)
            except (httpx.HTTPError, BlockedDestinationError) as problem:
                hop.error = error_name(problem)
        return hop

    def should_read_body(self, hop: HopResponse, read_any_body: bool) -> bool:
        if hop.is_redirect:
            return False
        content_type = hop.content_type
        return read_any_body or content_type is None or content_type in HTML_CONTENT_TYPES

    async def read_body(self, response: httpx.Response, hop: HopResponse, byte_limit: int) -> None:
        chunks: list[bytes] = []
        received = 0
        async for chunk in response.aiter_bytes():
            chunks.append(chunk)
            received += len(chunk)
            if received >= byte_limit:
                hop.body_truncated = received > byte_limit
                break
        hop.body = b"".join(chunks)[:byte_limit]
