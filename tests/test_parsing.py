from yarl import URL

from seowolf.parsing.content import count_words, decode_html
from seowolf.parsing.head_tags import robots_directives
from seowolf.parsing.indexability import IndexabilityInput, judge_indexability
from seowolf.parsing.page_parser import parse_page

__author__ = "@anhafxd"

PAGE_URL = URL("https://example.com/guides/boots")
SAMPLE_HTML = """<!doctype html><html lang="en-GB"><head>
<title> Winter   Boots </title><title>Second title</title>
<META NAME="Description" content="Warm boots">
<meta name="robots" content="NOINDEX, follow">
<link rel="Canonical" href="/guides/boots">
<base href="https://example.com/base/">
</head><body>
<svg><title>icon label</title></svg>
<nav><a href="/">Home</a></nav>
<main><h1>Boots</h1><h1>Again</h1>
<a href="sizes" rel="nofollow ugc">Size chart</a>
<a href="https://other.example/"><img src="badge.png" alt="Partner badge"></a>
<a href="#reviews">Reviews</a><a href="mailto:hi@example.com">Mail</a>
<img src="/img/boot.webp"><img src="data:image/png;base64,AAAA">
<link rel="stylesheet" href="/s.css"><script src="/app.js"></script>
<script>var hidden = "do not count these words";</script>
<p>Waterproof leather boots for snow.</p></main>
<footer><a href="/privacy">Privacy</a></footer>
</body></html>"""


def test_head_tags_are_extracted_without_svg_titles() -> None:
    parsed = parse_page(SAMPLE_HTML, PAGE_URL)
    assert parsed.head.titles == ["Winter Boots", "Second title"]
    assert parsed.head.meta_description == "Warm boots"
    assert parsed.head.robots_meta == ["noindex, follow"]
    assert parsed.head.canonical == "/guides/boots"
    assert parsed.head.lang == "en-GB"
    assert parsed.h1s == ["Boots", "Again"]


def test_links_use_base_href_and_carry_position_rel_and_anchor() -> None:
    parsed = parse_page(SAMPLE_HTML, PAGE_URL)
    links = {link.href: link for link in parsed.links}
    assert set(links) == {
        "/",
        "sizes",
        "https://other.example/",
        "/privacy",
        "mailto:hi@example.com",
    }
    assert links["mailto:hi@example.com"].url is None
    assert str(links["sizes"].url) == "https://example.com/base/sizes"
    assert links["sizes"].nofollow and links["sizes"].rel == ("nofollow", "ugc")
    assert links["/"].position == "nav"
    assert links["/privacy"].position == "footer"
    assert links["https://other.example/"].anchor_text == "Partner badge"


def test_resources_are_found_and_data_uris_ignored() -> None:
    parsed = parse_page(SAMPLE_HTML, PAGE_URL)
    found = {(resource.element, str(resource.url)) for resource in parsed.resources}
    assert ("image", "https://example.com/img/boot.webp") in found
    assert ("image", "https://example.com/base/badge.png") in found
    assert ("stylesheet", "https://example.com/s.css") in found
    assert ("script", "https://example.com/app.js") in found
    assert all(not str(url).startswith("data:") for _, url in found)


def test_word_count_ignores_scripts_and_handles_bengali() -> None:
    parsed = parse_page(SAMPLE_HTML, PAGE_URL)
    assert parsed.word_count == 13
    assert count_words("আমার সোনার বাংলা — ok") == 4


def test_charset_detection_from_meta_tag() -> None:
    body = '<meta charset="windows-1252"><p>caf\xe9</p>'.encode("cp1252")
    assert "café" in decode_html(body, "text/html")
    assert "café" in decode_html("café".encode(), "text/html; charset=utf-8")


def test_robots_directives_merge_meta_header_and_agent_specific_values() -> None:
    assert robots_directives(["none"], None) == {"noindex", "nofollow"}
    assert "noindex" in robots_directives([], "googlebot: noindex")
    assert "noindex" not in robots_directives([], "otherbot: noindex")
    assert robots_directives(["index, follow"], "noarchive") == {"index", "follow", "noarchive"}


def facts(**changes: object) -> IndexabilityInput:
    values: dict[str, object] = {
        "blocked_by_robots": False,
        "fetch_error": None,
        "status_code": 200,
        "is_html": True,
        "directives": frozenset(),
        "page_url": "https://example.com/a",
        "canonical_url": None,
    }
    values.update(changes)
    return IndexabilityInput(**values)


def test_indexability_reasons() -> None:
    assert judge_indexability(facts()) == (True, "indexable")
    assert judge_indexability(facts(directives=frozenset({"noindex"})))[1] == "noindex"
    assert judge_indexability(facts(canonical_url="https://example.com/b"))[1] == "canonicalised"
    assert judge_indexability(facts(status_code=404))[1] == "client_error"
    assert judge_indexability(facts(status_code=301))[1] == "redirect"
    assert judge_indexability(facts(blocked_by_robots=True))[1] == "blocked_by_robots"
    assert judge_indexability(facts(is_html=False))[1] == "non_html"
