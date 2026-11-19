from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from seowolf.crawler.fetcher import PageFetcher
from seowolf.crawler.options import CrawlOptions
from seowolf.crawler.politeness import HostThrottle
from seowolf.signature import DEFAULT_USER_AGENT

__author__ = "@anhafxd"

SITE = "https://shop.example.test"
PAGE = "<html><head><title>Shop</title></head><body>ok</body></html>"


@pytest.fixture
async def fetcher() -> AsyncIterator[PageFetcher]:
    options = CrawlOptions(
        start_url=f"{SITE}/", per_host_delay=0, max_redirect_hops=3, max_body_bytes=2048
    )
    page_fetcher = PageFetcher(options, HostThrottle(0, 4))
    yield page_fetcher
    await page_fetcher.close()


@respx.mock
async def test_every_redirect_hop_is_recorded(fetcher: PageFetcher) -> None:
    respx.get(f"{SITE}/old").mock(return_value=httpx.Response(301, headers={"Location": "/mid"}))
    respx.get(f"{SITE}/mid").mock(return_value=httpx.Response(302, headers={"Location": "/new"}))
    respx.get(f"{SITE}/new").mock(return_value=httpx.Response(200, html=PAGE))
    result = await fetcher.fetch(f"{SITE}/old")
    assert [hop.status_code for hop in result.hops] == [301, 302, 200]
    assert result.final_url == f"{SITE}/new"
    assert result.was_redirected and result.error is None
    assert b"<title>Shop</title>" in result.final.body


@respx.mock
async def test_redirect_loops_are_detected(fetcher: PageFetcher) -> None:
    respx.get(f"{SITE}/a").mock(return_value=httpx.Response(302, headers={"Location": "/b"}))
    respx.get(f"{SITE}/b").mock(return_value=httpx.Response(302, headers={"Location": "/a"}))
    result = await fetcher.fetch(f"{SITE}/a")
    assert result.redirect_loop
    assert result.error == "redirect_loop"


@respx.mock
async def test_too_many_redirects_stop_the_chain(fetcher: PageFetcher) -> None:
    for number in range(6):
        respx.get(f"{SITE}/hop{number}").mock(
            return_value=httpx.Response(301, headers={"Location": f"/hop{number + 1}"})
        )
    result = await fetcher.fetch(f"{SITE}/hop0")
    assert result.error == "too_many_redirects"
    assert len(result.hops) == 4


@respx.mock
async def test_rate_limited_requests_are_retried(fetcher: PageFetcher) -> None:
    route = respx.get(f"{SITE}/busy").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, html=PAGE),
        ]
    )
    result = await fetcher.fetch(f"{SITE}/busy")
    assert route.call_count == 2
    assert result.final.status_code == 200


@respx.mock
async def test_bodies_are_capped_and_binary_bodies_skipped(fetcher: PageFetcher) -> None:
    respx.get(f"{SITE}/huge").mock(return_value=httpx.Response(200, html="x" * 10_000))
    respx.get(f"{SITE}/photo.png").mock(
        return_value=httpx.Response(
            200, content=b"\x89PNG" * 100, headers={"Content-Type": "image/png"}
        )
    )
    huge = await fetcher.fetch(f"{SITE}/huge")
    assert len(huge.final.body) == 2048 and huge.final.body_truncated
    photo = await fetcher.fetch(f"{SITE}/photo.png")
    assert photo.final.body == b"" and photo.final.content_type == "image/png"


@respx.mock
async def test_head_falls_back_to_ranged_get(fetcher: PageFetcher) -> None:
    respx.head(f"{SITE}/file.pdf").mock(return_value=httpx.Response(405))
    ranged = respx.get(f"{SITE}/file.pdf").mock(
        return_value=httpx.Response(206, content=b"%", headers={"Content-Range": "bytes 0-0/5000"})
    )
    result = await fetcher.check_status(f"{SITE}/file.pdf")
    assert result.final.status_code == 206
    assert ranged.calls.last.request.headers["Range"] == "bytes=0-0"


@respx.mock
async def test_honest_user_agent_is_sent(fetcher: PageFetcher) -> None:
    route = respx.get(f"{SITE}/").mock(return_value=httpx.Response(200, html=PAGE))
    await fetcher.fetch(f"{SITE}/")
    assert route.calls.last.request.headers["User-Agent"] == DEFAULT_USER_AGENT


@respx.mock
async def test_timeouts_become_named_errors(fetcher: PageFetcher) -> None:
    respx.get(f"{SITE}/slow").mock(side_effect=httpx.ReadTimeout("slow"))
    fetcher.options.max_retries = 0
    result = await fetcher.fetch(f"{SITE}/slow")
    assert result.error == "timeout"
