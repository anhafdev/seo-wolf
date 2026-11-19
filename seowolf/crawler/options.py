import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from yarl import URL

from seowolf.signature import DEFAULT_USER_AGENT

__author__ = "@anhafxd"

TRACKING_PARAMETERS = ["utm_*", "gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "_ga", "_gl"]


class CrawlOptions(BaseModel):
    start_url: str
    mode: Literal["fast"] = "fast"
    list_mode: bool = False
    url_list: list[str] = Field(default_factory=list)
    sitemap_urls: list[str] = Field(default_factory=list)
    use_robots_sitemaps: bool = True
    max_urls: int = Field(default=50_000, ge=1)
    max_resources: int = Field(default=100_000, ge=0)
    max_depth: int | None = Field(default=None, ge=0)
    concurrency: int = Field(default=4, ge=1, le=64)
    per_host_concurrency: int = Field(default=4, ge=1, le=64)
    per_host_delay: float = Field(default=0.25, ge=0)
    timeout_seconds: float = Field(default=20.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    max_redirect_hops: int = Field(default=10, ge=1, le=20)
    respect_robots: bool = True
    user_agent: str | None = None
    custom_headers: dict[str, str] = Field(default_factory=dict)
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    subdomain_policy: Literal["same_host", "all_subdomains"] = "same_host"
    query_policy: Literal["keep", "strip_listed", "strip_all"] = "keep"
    stripped_parameters: list[str] = Field(default_factory=lambda: list(TRACKING_PARAMETERS))
    trailing_slash: Literal["keep", "add", "remove"] = "keep"
    follow_nofollow: bool = False
    check_resources: bool = True
    check_external_links: bool = True
    allow_private_networks: bool = False
    store_html: bool = False
    max_html_bytes: int = Field(default=2_000_000, ge=1)
    max_body_bytes: int = Field(default=10_000_000, ge=1)

    @field_validator("start_url")
    @classmethod
    def start_url_must_be_web_address(cls, value: str) -> str:
        parsed = URL(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.host:
            raise ValueError("start_url must be an absolute http or https address")
        return str(parsed)

    @field_validator("include_patterns", "exclude_patterns")
    @classmethod
    def patterns_must_compile(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as problem:
                raise ValueError(f"invalid regex {pattern!r}: {problem}") from problem
        return patterns

    @property
    def effective_user_agent(self) -> str:
        return self.user_agent or DEFAULT_USER_AGENT
