import re
import zlib
from dataclasses import dataclass, field
from xml.etree import ElementTree

from yarl import URL

from seowolf.crawler.fetcher import PageFetcher
from seowolf.crawler.url_rules import parse_web_url

__author__ = "@anhafxd"

MAX_SITEMAP_BYTES = 50 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 60 * 1024 * 1024
GZIP_MAGIC = b"\x1f\x8b"
FORBIDDEN_XML = re.compile(rb"<!(DOCTYPE|ENTITY)", re.IGNORECASE)


class SitemapTooLargeError(Exception):
    def __init__(self) -> None:
        super().__init__(f"sitemap exceeds {MAX_SITEMAP_BYTES // (1024 * 1024)} MB uncompressed")


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: str | None = None


@dataclass
class SitemapDocument:
    kind: str
    entries: list[SitemapEntry] = field(default_factory=list)
    error: str | None = None


@dataclass
class SitemapReport:
    url: str
    status_code: int | None
    kind: str
    url_count: int
    byte_size: int
    gzipped: bool
    error: str | None
    parent_url: str | None


def inflate_if_gzipped(body: bytes) -> tuple[bytes, bool]:
    if not body.startswith(GZIP_MAGIC):
        return body, False
    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    inflated = inflater.decompress(body, MAX_SITEMAP_BYTES + 1)
    if len(inflated) > MAX_SITEMAP_BYTES or inflater.unconsumed_tail:
        raise SitemapTooLargeError
    return inflated, True


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ElementTree.Element, name: str) -> str | None:
    for child in element:
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def parse_text_sitemap(text: str) -> SitemapDocument:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    entries = [SitemapEntry(loc=line) for line in lines if parse_web_url(line) is not None]
    return SitemapDocument(kind="text" if entries else "invalid", entries=entries)


def parse_sitemap(body: bytes) -> SitemapDocument:
    stripped = body.lstrip()
    if not stripped.startswith(b"<"):
        return parse_text_sitemap(body.decode("utf-8", errors="replace"))
    if FORBIDDEN_XML.search(stripped):
        return SitemapDocument(kind="invalid", error="doctype_not_allowed")
    try:
        root = ElementTree.fromstring(stripped)
    except ElementTree.ParseError as problem:
        return SitemapDocument(kind="invalid", error=f"xml_parse_error: {problem}")
    root_name = local_name(root.tag)
    item_name = {"urlset": "url", "sitemapindex": "sitemap"}.get(root_name)
    if item_name is None:
        return SitemapDocument(kind="invalid", error=f"unexpected_root: {root_name}")
    entries = []
    for element in root:
        if local_name(element.tag) != item_name:
            continue
        location = child_text(element, "loc")
        if location:
            entries.append(SitemapEntry(loc=location, lastmod=child_text(element, "lastmod")))
    kind = "index" if root_name == "sitemapindex" else "urlset"
    return SitemapDocument(kind=kind, entries=entries)


class SitemapCollector:
    def __init__(self, fetcher: PageFetcher, max_urls: int, max_sitemaps: int = 500) -> None:
        self.fetcher = fetcher
        self.max_urls = max_urls
        self.max_sitemaps = max_sitemaps
        self.reports: list[SitemapReport] = []
        self.entries: list[tuple[str, SitemapEntry]] = []

    async def collect(self, sitemap_urls: list[str]) -> list[tuple[str, SitemapEntry]]:
        pending: list[tuple[str, str | None]] = [(url, None) for url in sitemap_urls]
        seen: set[str] = set()
        while pending and len(seen) < self.max_sitemaps and len(self.entries) < self.max_urls:
            sitemap_url, parent_url = pending.pop(0)
            if sitemap_url in seen:
                continue
            seen.add(sitemap_url)
            document = await self.read_sitemap(sitemap_url, parent_url)
            if document.kind == "index":
                pending.extend((entry.loc, sitemap_url) for entry in document.entries)
                continue
            room = self.max_urls - len(self.entries)
            self.entries.extend((sitemap_url, entry) for entry in document.entries[:room])
        return self.entries

    async def read_sitemap(self, sitemap_url: str, parent_url: str | None) -> SitemapDocument:
        if parse_web_url(sitemap_url) is None:
            return self.record(sitemap_url, None, SitemapDocument("invalid", error="invalid_url"))
        result = await self.fetcher.fetch(
            sitemap_url, read_any_body=True, max_bytes=MAX_DOWNLOAD_BYTES
        )
        status_code = result.final.status_code if result.hops else None
        if result.error or status_code is None or not 200 <= status_code < 300:
            failure = SitemapDocument("invalid", error=result.error or f"status_{status_code}")
            return self.record(sitemap_url, status_code, failure, parent_url=parent_url)
        raw_body = result.final.body
        try:
            body, gzipped = inflate_if_gzipped(raw_body)
        except (SitemapTooLargeError, zlib.error) as problem:
            failure = SitemapDocument("invalid", error=str(problem))
            return self.record(sitemap_url, status_code, failure, len(raw_body), True, parent_url)
        document = parse_sitemap(body)
        return self.record(sitemap_url, status_code, document, len(body), gzipped, parent_url)

    def record(
        self,
        url: str,
        status_code: int | None,
        document: SitemapDocument,
        byte_size: int = 0,
        gzipped: bool = False,
        parent_url: str | None = None,
    ) -> SitemapDocument:
        report = SitemapReport(
            url=url,
            status_code=status_code,
            kind=document.kind,
            url_count=len(document.entries),
            byte_size=byte_size,
            gzipped=gzipped,
            error=document.error,
            parent_url=parent_url,
        )
        self.reports.append(report)
        return document


def default_sitemap_url(start_url: str) -> str:
    return str(URL(start_url).origin() / "sitemap.xml")
