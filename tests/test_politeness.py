import time
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from seowolf.crawler.politeness import HostThrottle, parse_retry_after

__author__ = "@anhafxd"


def test_retry_after_seconds_dates_and_garbage() -> None:
    assert parse_retry_after("7") == 7
    assert parse_retry_after("100000") == 300
    assert parse_retry_after("soon") is None
    assert parse_retry_after(None) is None
    in_ten_seconds = format_datetime(datetime.now(UTC) + timedelta(seconds=10), usegmt=True)
    waited = parse_retry_after(in_ten_seconds)
    assert waited is not None and 5 <= waited <= 10


async def test_requests_to_one_host_are_spaced_out() -> None:
    throttle = HostThrottle(base_delay=0.05, per_host_limit=4)
    started = time.monotonic()
    for _ in range(3):
        async with throttle.slot("example.com"):
            continue
    assert time.monotonic() - started >= 0.08


async def test_different_hosts_do_not_wait_for_each_other() -> None:
    throttle = HostThrottle(base_delay=0.2, per_host_limit=4)
    started = time.monotonic()
    for host in ("a.example", "b.example", "c.example"):
        async with throttle.slot(host):
            continue
    assert time.monotonic() - started < 0.15


def test_backoff_grows_and_recovers() -> None:
    throttle = HostThrottle(base_delay=0.25, per_host_limit=4)
    state = throttle.state_for("example.com")
    calm_spacing = throttle.spacing_for(state)
    throttle.slow_down("example.com", retry_after=None)
    throttle.slow_down("example.com", retry_after=None)
    assert throttle.spacing_for(state) > calm_spacing
    throttle.recover("example.com")
    throttle.recover("example.com")
    assert throttle.spacing_for(state) == calm_spacing


def test_crawl_delay_is_capped() -> None:
    throttle = HostThrottle(base_delay=0.0, per_host_limit=1)
    throttle.apply_crawl_delay("example.com", 3600)
    assert throttle.state_for("example.com").crawl_delay == 30
