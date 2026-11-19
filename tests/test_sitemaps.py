import gzip

import pytest

from seowolf.crawler.sitemaps import (
    MAX_SITEMAP_BYTES,
    SitemapTooLargeError,
    inflate_if_gzipped,
    parse_sitemap,
)

__author__ = "@anhafxd"

URLSET = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc> https://example.com/a </loc><lastmod>2026-01-02</lastmod></url>
  <url><loc>https://example.com/b</loc></url>
  <url><lastmod>2026-01-02</lastmod></url>
</urlset>"""

INDEX = b"""<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/posts.xml.gz</loc></sitemap>
</sitemapindex>"""


def test_urlset_entries_and_lastmod_are_read() -> None:
    document = parse_sitemap(URLSET)
    assert document.kind == "urlset"
    assert [entry.loc for entry in document.entries] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert document.entries[0].lastmod == "2026-01-02"
    assert document.entries[1].lastmod is None


def test_sitemap_index_is_recognised() -> None:
    document = parse_sitemap(INDEX)
    assert document.kind == "index"
    assert document.entries[0].loc == "https://example.com/posts.xml.gz"


def test_gzip_sitemaps_are_inflated() -> None:
    body, gzipped = inflate_if_gzipped(gzip.compress(URLSET))
    assert gzipped
    assert parse_sitemap(body).kind == "urlset"


def test_gzip_bombs_are_refused() -> None:
    bomb = gzip.compress(b"<" + b"a" * (MAX_SITEMAP_BYTES + 10))
    with pytest.raises(SitemapTooLargeError):
        inflate_if_gzipped(bomb)


def test_plain_text_sitemaps_are_supported() -> None:
    document = parse_sitemap(b"https://example.com/one\n\nnot a url\nhttps://example.com/two\n")
    assert document.kind == "text"
    assert len(document.entries) == 2


def test_doctype_and_entities_are_refused() -> None:
    hostile = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "boom">]><urlset></urlset>'
    document = parse_sitemap(hostile)
    assert document.kind == "invalid"
    assert document.error == "doctype_not_allowed"


def test_broken_xml_reports_an_error() -> None:
    document = parse_sitemap(b"<urlset><url><loc>https://example.com/</url>")
    assert document.kind == "invalid"
    assert document.error and document.error.startswith("xml_parse_error")
