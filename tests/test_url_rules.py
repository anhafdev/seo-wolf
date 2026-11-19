import pytest
from yarl import URL

from seowolf.crawler.options import CrawlOptions
from seowolf.crawler.url_rules import UrlPolicy, UrlScope, normalise_text, parse_web_url

__author__ = "@anhafxd"

KEEP = UrlPolicy()
STRIP_TRACKING = UrlPolicy(query_policy="strip_listed", stripped_parameters=("utm_*", "gclid"))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HTTP://Example.COM:80/a/./b/../c#part", "http://example.com/a/c"),
        ("https://example.com:443", "https://example.com/"),
        ("https://user:secret@example.com/x", "https://example.com/x"),
        ("https://example.com/%7euser/", "https://example.com/~user/"),
        ("https://example.com/page?", "https://example.com/page"),
        ("https://example.com:8443/p", "https://example.com:8443/p"),
    ],
)
def test_normalisation_cleans_addresses(raw: str, expected: str) -> None:
    assert normalise_text(raw, KEEP) == expected


def test_relative_and_protocol_relative_links_resolve_against_base() -> None:
    base = URL("https://example.com/blog/post")
    assert normalise_text("../about", KEEP, base) == "https://example.com/about"
    assert normalise_text("//cdn.example.net/a.js", KEEP, base) == "https://cdn.example.net/a.js"
    assert normalise_text("?page=2", KEEP, base) == "https://example.com/blog/post?page=2"


@pytest.mark.parametrize(
    "raw", ["mailto:hi@example.com", "javascript:void(0)", "tel:+100", "", "http://exa mple.com/"]
)
def test_non_web_addresses_are_rejected(raw: str) -> None:
    assert parse_web_url(raw) is None


def test_tracking_parameters_are_stripped_but_others_kept() -> None:
    raw = "https://example.com/shoes?utm_source=mail&size=42&gclid=abc"
    assert normalise_text(raw, STRIP_TRACKING) == "https://example.com/shoes?size=42"
    assert normalise_text(raw, UrlPolicy(query_policy="strip_all")) == "https://example.com/shoes"


@pytest.mark.parametrize(
    ("policy", "raw", "expected"),
    [
        ("add", "https://example.com/docs", "https://example.com/docs/"),
        ("add", "https://example.com/file.pdf", "https://example.com/file.pdf"),
        ("remove", "https://example.com/docs/", "https://example.com/docs"),
        ("remove", "https://example.com/", "https://example.com/"),
    ],
)
def test_trailing_slash_policy(policy: str, raw: str, expected: str) -> None:
    assert normalise_text(raw, UrlPolicy(trailing_slash=policy)) == expected


def test_scope_treats_www_twin_as_internal_and_other_subdomains_as_external() -> None:
    scope = UrlScope(CrawlOptions(start_url="https://example.com/"))
    assert scope.is_internal(URL("https://www.example.com/a"))
    assert scope.is_internal(URL("http://example.com/a"))
    assert not scope.is_internal(URL("https://shop.example.com/a"))


def test_scope_can_include_all_subdomains() -> None:
    options = CrawlOptions(start_url="https://www.example.com/", subdomain_policy="all_subdomains")
    scope = UrlScope(options)
    assert scope.is_internal(URL("https://shop.example.com/a"))
    assert not scope.is_internal(URL("https://notexample.com/a"))


def test_include_and_exclude_patterns_filter_urls() -> None:
    options = CrawlOptions(
        start_url="https://example.com/", include_patterns=["/blog/"], exclude_patterns=["/tag/"]
    )
    scope = UrlScope(options)
    assert scope.passes_filters("https://example.com/blog/post")
    assert not scope.passes_filters("https://example.com/blog/tag/news")
    assert not scope.passes_filters("https://example.com/shop/")


def test_invalid_regex_is_rejected_by_options() -> None:
    with pytest.raises(ValueError, match="invalid regex"):
        CrawlOptions(start_url="https://example.com/", include_patterns=["(unclosed"])
