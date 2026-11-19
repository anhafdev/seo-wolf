from dataclasses import dataclass, field

__author__ = "@anhafxd"

HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


@dataclass
class HopResponse:
    url: str
    status_code: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    body_truncated: bool = False
    response_ms: int | None = None
    http_version: str | None = None
    error: str | None = None

    @property
    def content_type(self) -> str | None:
        value = self.headers.get("content-type")
        return value.split(";", 1)[0].strip().lower() if value else None

    @property
    def location(self) -> str | None:
        return self.headers.get("location")

    @property
    def is_redirect(self) -> bool:
        return self.status_code in REDIRECT_STATUSES and bool(self.location)

    def as_chain_entry(self) -> dict[str, object]:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "location": self.location,
            "response_ms": self.response_ms,
        }


@dataclass
class FetchResult:
    requested_url: str
    hops: list[HopResponse] = field(default_factory=list)
    redirect_loop: bool = False
    chain_error: str | None = None

    @property
    def first(self) -> HopResponse:
        return self.hops[0]

    @property
    def final(self) -> HopResponse:
        return self.hops[-1]

    @property
    def final_url(self) -> str:
        return self.final.url if self.hops else self.requested_url

    @property
    def was_redirected(self) -> bool:
        return len(self.hops) > 1 or (bool(self.hops) and self.first.is_redirect)

    @property
    def error(self) -> str | None:
        return self.chain_error or (self.final.error if self.hops else "not_fetched")

    @property
    def final_is_html(self) -> bool:
        content_type = self.final.content_type
        return content_type is None or content_type in HTML_CONTENT_TYPES

    def redirect_chain(self) -> list[dict[str, object]]:
        return [hop.as_chain_entry() for hop in self.hops]
