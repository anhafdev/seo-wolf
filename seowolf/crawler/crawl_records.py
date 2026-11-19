from dataclasses import asdict, dataclass, field
from typing import Any

__author__ = "@anhafxd"

PAGE_KIND = "page"
STATUS_ONLY_KINDS = ("image", "script", "stylesheet", "external")


@dataclass
class DiscoveredUrl:
    url: str
    original_url: str
    kind: str
    depth: int
    discovered_from: str | None


@dataclass
class LinkRecord:
    to_url: str | None
    href: str
    element: str
    anchor_text: str
    rel: str
    is_internal: bool
    nofollow: bool
    position: str


@dataclass
class RedirectRecord:
    source_url: str
    final_url: str
    final_status_code: int | None
    hop_count: int
    is_loop: bool
    error: str | None
    chain: list[dict[str, Any]]


@dataclass
class PageRecord:
    url: str
    final_url: str
    depth: int
    status_code: int | None = None
    fetch_error: str | None = None
    content_type: str | None = None
    bytes: int = 0
    response_ms: int | None = None
    http_version: str | None = None
    indexable: bool = False
    indexability_reason: str = ""
    title: str | None = None
    meta_description: str | None = None
    h1: str | None = None
    canonical: str | None = None
    robots_meta: str | None = None
    x_robots_tag: str | None = None
    word_count: int = 0
    text_ratio: float = 0.0
    lang: str | None = None
    head_data: dict[str, Any] = field(default_factory=dict)
    response_headers: dict[str, Any] = field(default_factory=dict)
    html: str | None = None
    links: list[LinkRecord] = field(default_factory=list)
    redirect: RedirectRecord | None = None

    def column_values(self) -> dict[str, Any]:
        values = asdict(self)
        values.pop("links")
        values.pop("redirect")
        return values


@dataclass
class ResourceRecord:
    url: str
    kind: str
    final_url: str
    is_internal: bool
    status_code: int | None = None
    final_status_code: int | None = None
    content_type: str | None = None
    bytes: int | None = None
    response_ms: int | None = None
    error: str | None = None


@dataclass
class CrawlOutcome:
    frontier_id: int
    state: str = "done"
    pages: list[PageRecord] = field(default_factory=list)
    resource: ResourceRecord | None = None
    discovered: list[DiscoveredUrl] = field(default_factory=list)
    completed: list[DiscoveredUrl] = field(default_factory=list)
    error: str | None = None
