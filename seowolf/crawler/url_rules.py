import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from urllib.parse import unquote

from yarl import URL

from seowolf.crawler.options import CrawlOptions

__author__ = "@anhafxd"

WEB_SCHEMES = {"http", "https"}
INVISIBLE_URL_CHARACTERS = re.compile(r"[\t\n\r]")
VALID_HOST = re.compile(r"^[a-z0-9._-]+$|^[0-9a-f:.]+$")


@dataclass(frozen=True)
class UrlPolicy:
    query_policy: str = "keep"
    stripped_parameters: tuple[str, ...] = ()
    trailing_slash: str = "keep"

    @classmethod
    def from_options(cls, options: CrawlOptions) -> "UrlPolicy":
        return cls(
            query_policy=options.query_policy,
            stripped_parameters=tuple(options.stripped_parameters),
            trailing_slash=options.trailing_slash,
        )


def parse_web_url(raw: str, base: URL | None = None) -> URL | None:
    text = INVISIBLE_URL_CHARACTERS.sub("", raw.strip())
    if not text:
        return None
    try:
        candidate = URL(text)
        if base is not None and not candidate.scheme:
            candidate = base.join(candidate)
    except (ValueError, TypeError):
        return None
    if candidate.scheme not in WEB_SCHEMES or not candidate.raw_host:
        return None
    if not VALID_HOST.match(candidate.raw_host.lower()):
        return None
    return candidate


def parameter_is_stripped(name: str, stripped_parameters: tuple[str, ...]) -> bool:
    lowered = name.lower()
    return any(fnmatchcase(lowered, pattern.lower()) for pattern in stripped_parameters)


def filtered_query(raw_query: str, policy: UrlPolicy) -> str:
    if policy.query_policy == "strip_all":
        return ""
    pairs = [pair for pair in raw_query.split("&") if pair]
    if policy.query_policy == "strip_listed":
        pairs = [
            pair
            for pair in pairs
            if not parameter_is_stripped(unquote(pair.split("=", 1)[0]), policy.stripped_parameters)
        ]
    return "&".join(pairs)


def adjusted_path(path: str, trailing_slash: str) -> str:
    if not path:
        return "/"
    if path == "/" or trailing_slash == "keep":
        return path
    if trailing_slash == "remove":
        return path.rstrip("/") or "/"
    last_segment = path.rsplit("/", 1)[-1]
    if path.endswith("/") or "." in last_segment:
        return path
    return path + "/"


def normalise_url(url: URL, policy: UrlPolicy) -> str:
    cleaned = url.with_fragment(None).with_user(None).with_password(None)
    path = adjusted_path(cleaned.raw_path, policy.trailing_slash)
    query = filtered_query(cleaned.raw_query_string, policy)
    base = str(cleaned.with_query(None).with_path(path, encoded=True))
    return f"{base}?{query}" if query else base


def normalise_text(raw: str, policy: UrlPolicy, base: URL | None = None) -> str | None:
    parsed = parse_web_url(raw, base)
    return normalise_url(parsed, policy) if parsed is not None else None


def host_twins(host: str) -> set[str]:
    bare = host.removeprefix("www.")
    return {bare, f"www.{bare}"}


class UrlScope:
    def __init__(self, options: CrawlOptions) -> None:
        start = URL(options.start_url)
        self.start_host = (start.host or "").lower()
        self.root_host = self.start_host.removeprefix("www.")
        self.allowed_hosts = host_twins(self.start_host)
        self.include_all_subdomains = options.subdomain_policy == "all_subdomains"
        self.includes = [re.compile(pattern) for pattern in options.include_patterns]
        self.excludes = [re.compile(pattern) for pattern in options.exclude_patterns]

    def is_internal(self, url: URL) -> bool:
        host = (url.host or "").lower()
        if host in self.allowed_hosts:
            return True
        return self.include_all_subdomains and host.endswith(f".{self.root_host}")

    def passes_filters(self, url_text: str) -> bool:
        if self.includes and not any(pattern.search(url_text) for pattern in self.includes):
            return False
        return not any(pattern.search(url_text) for pattern in self.excludes)

    def should_crawl(self, url: URL, url_text: str) -> bool:
        return self.is_internal(url) and self.passes_filters(url_text)
