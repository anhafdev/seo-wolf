from yarl import URL

from seowolf.crawler.crawl_records import LinkRecord, PageRecord, RedirectRecord
from seowolf.crawler.fetch_result import FetchResult, HopResponse
from seowolf.crawler.url_rules import UrlPolicy, UrlScope, normalise_text, normalise_url
from seowolf.parsing.content import decode_html
from seowolf.parsing.head_tags import robots_directives
from seowolf.parsing.indexability import IndexabilityInput, judge_indexability
from seowolf.parsing.page_parser import ParsedPage, parse_page

__author__ = "@anhafxd"

KEPT_RESPONSE_HEADERS = (
    "content-type",
    "content-length",
    "content-encoding",
    "cache-control",
    "last-modified",
    "etag",
    "x-robots-tag",
    "link",
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "referrer-policy",
    "x-frame-options",
    "server",
    "vary",
)


def kept_headers(hop: HopResponse) -> dict[str, str]:
    return {name: hop.headers[name] for name in KEPT_RESPONSE_HEADERS if name in hop.headers}


def link_records(parsed: ParsedPage, scope: UrlScope, policy: UrlPolicy) -> list[LinkRecord]:
    records = []
    for link in [*parsed.links, *parsed.resources]:
        records.append(
            LinkRecord(
                to_url=normalise_url(link.url, policy) if link.url is not None else None,
                href=link.href[:4096],
                element=link.element,
                anchor_text=link.anchor_text[:2000],
                rel=" ".join(link.rel),
                is_internal=link.url is not None and scope.is_internal(link.url),
                nofollow=link.nofollow,
                position=link.position,
            )
        )
    return records


def redirect_record(result: FetchResult) -> RedirectRecord:
    return RedirectRecord(
        source_url=result.requested_url,
        final_url=result.final_url,
        final_status_code=result.final.status_code,
        hop_count=len(result.hops) - 1 if not result.chain_error else len(result.hops),
        is_loop=result.redirect_loop,
        error=result.chain_error,
        chain=result.redirect_chain(),
    )


def redirect_page_record(url: str, depth: int, result: FetchResult) -> PageRecord:
    first = result.first
    return PageRecord(
        url=url,
        final_url=result.final_url,
        depth=depth,
        status_code=first.status_code,
        fetch_error=result.chain_error,
        response_ms=first.response_ms,
        http_version=first.http_version,
        indexable=False,
        indexability_reason="redirect",
        response_headers=kept_headers(first),
        redirect=redirect_record(result),
    )


def blocked_page_record(url: str, depth: int) -> PageRecord:
    return PageRecord(
        url=url,
        final_url=url,
        depth=depth,
        fetch_error="blocked_by_robots",
        indexable=False,
        indexability_reason="blocked_by_robots",
    )


def content_page_record(
    url: str,
    depth: int,
    hop: HopResponse,
    is_html: bool,
    scope: UrlScope,
    policy: UrlPolicy,
    store_html_bytes: int | None,
) -> tuple[PageRecord, ParsedPage | None]:
    record = PageRecord(
        url=url,
        final_url=url,
        depth=depth,
        status_code=hop.status_code,
        fetch_error=hop.error,
        content_type=hop.content_type,
        bytes=len(hop.body) or int(hop.headers.get("content-length", "0") or 0),
        response_ms=hop.response_ms,
        http_version=hop.http_version,
        x_robots_tag=hop.headers.get("x-robots-tag"),
        response_headers=kept_headers(hop),
    )
    parsed: ParsedPage | None = None
    if is_html and hop.body and hop.error is None:
        html = decode_html(hop.body, hop.headers.get("content-type"))
        parsed = parse_page(html, URL(url))
        fill_from_parsed(record, parsed, policy)
        record.links = link_records(parsed, scope, policy)
        if store_html_bytes is not None:
            record.html = html[:store_html_bytes]
    directives = robots_directives(parsed.head.robots_meta if parsed else [], record.x_robots_tag)
    record.indexable, record.indexability_reason = judge_indexability(
        IndexabilityInput(
            blocked_by_robots=False,
            fetch_error=hop.error,
            status_code=hop.status_code,
            is_html=is_html,
            directives=frozenset(directives),
            page_url=url,
            canonical_url=record.canonical,
        )
    )
    return record, parsed


def fill_from_parsed(record: PageRecord, parsed: ParsedPage, policy: UrlPolicy) -> None:
    head = parsed.head
    record.title = head.title
    record.meta_description = head.meta_description
    record.h1 = parsed.h1
    record.lang = head.lang
    record.robots_meta = ", ".join(head.robots_meta) or None
    record.word_count = parsed.word_count
    record.text_ratio = parsed.text_ratio
    if head.canonical:
        record.canonical = normalise_text(head.canonical, policy, URL(record.url))
    record.head_data = {
        "titles": head.titles,
        "meta_descriptions": head.meta_descriptions,
        "canonicals": head.canonicals,
        "robots_meta": head.robots_meta,
        "h1s": parsed.h1s,
        "base_href": head.base_href,
        "viewport": head.viewport,
        "charset": head.charset,
    }
