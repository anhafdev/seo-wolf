import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

__author__ = "@anhafxd"

MAX_CRAWL_DELAY = 30.0
MAX_BACKOFF_SECONDS = 120.0
MAX_RETRY_AFTER = 300.0
MAX_BACKOFF_LEVEL = 6


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    text = value.strip()
    if text.isdigit():
        return min(float(text), MAX_RETRY_AFTER)
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    seconds = (moment - datetime.now(UTC)).total_seconds()
    return min(max(seconds, 0.0), MAX_RETRY_AFTER)


@dataclass
class HostState:
    semaphore: asyncio.Semaphore
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    next_allowed_at: float = 0.0
    paused_until: float = 0.0
    crawl_delay: float = 0.0
    backoff_level: int = 0


class HostThrottle:
    def __init__(self, base_delay: float, per_host_limit: int) -> None:
        self.base_delay = base_delay
        self.per_host_limit = per_host_limit
        self.hosts: dict[str, HostState] = {}

    def state_for(self, host: str) -> HostState:
        key = host.lower()
        if key not in self.hosts:
            self.hosts[key] = HostState(semaphore=asyncio.Semaphore(self.per_host_limit))
        return self.hosts[key]

    def apply_crawl_delay(self, host: str, seconds: float | None) -> None:
        if seconds is not None:
            self.state_for(host).crawl_delay = min(seconds, MAX_CRAWL_DELAY)

    def spacing_for(self, state: HostState) -> float:
        base = max(self.base_delay, state.crawl_delay)
        if state.backoff_level == 0:
            return base
        return min(max(base, 0.5) * (2**state.backoff_level), MAX_BACKOFF_SECONDS)

    def slow_down(self, host: str, retry_after: float | None) -> float:
        state = self.state_for(host)
        state.backoff_level = min(state.backoff_level + 1, MAX_BACKOFF_LEVEL)
        pause = retry_after if retry_after is not None else self.spacing_for(state)
        state.paused_until = max(state.paused_until, time.monotonic() + pause)
        return pause

    def recover(self, host: str) -> None:
        state = self.state_for(host)
        if state.backoff_level > 0:
            state.backoff_level -= 1

    @asynccontextmanager
    async def slot(self, host: str) -> AsyncIterator[None]:
        state = self.state_for(host)
        async with state.semaphore:
            async with state.lock:
                wait = max(state.next_allowed_at, state.paused_until) - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                state.next_allowed_at = time.monotonic() + self.spacing_for(state)
            yield
