from yarl import URL

from seowolf.crawler.robots import parse_robots, policy_from_response

__author__ = "@anhafxd"

ROBOTS_TEXT = """
User-agent: *
Disallow: /private/
Allow: /private/press-kit
Disallow: /*.pdf$
Disallow: /search?

User-agent: seowolf
User-agent: otherbot
Disallow: /drafts/
Crawl-delay: 2

Sitemap: https://example.com/sitemap.xml
"""


def allowed(policy_text: str, path: str, agent: str = "anybot") -> bool:
    return parse_robots(policy_text).is_allowed(URL(f"https://example.com{path}"), agent)


def test_named_group_wins_over_wildcard_group() -> None:
    assert allowed(ROBOTS_TEXT, "/private/x", "seowolf")
    assert not allowed(ROBOTS_TEXT, "/drafts/a", "seowolf")
    assert not allowed(ROBOTS_TEXT, "/drafts/a", "OtherBot")


def test_longest_match_and_allow_override() -> None:
    assert not allowed(ROBOTS_TEXT, "/private/team")
    assert allowed(ROBOTS_TEXT, "/private/press-kit/logo.png")


def test_wildcard_and_end_anchor() -> None:
    assert not allowed(ROBOTS_TEXT, "/files/report.pdf")
    assert allowed(ROBOTS_TEXT, "/files/report.pdf?download=1")
    assert not allowed(ROBOTS_TEXT, "/search?q=boots")
    assert allowed(ROBOTS_TEXT, "/search")


def test_equal_length_tie_prefers_allow() -> None:
    text = "User-agent: *\nDisallow: /page\nAllow: /page\n"
    assert allowed(text, "/page")


def test_empty_disallow_allows_everything_and_robots_file_is_always_allowed() -> None:
    assert allowed("User-agent: *\nDisallow:\n", "/anything")
    assert allowed("User-agent: *\nDisallow: /\n", "/robots.txt")


def test_crawl_delay_and_sitemaps_are_read() -> None:
    policy = parse_robots(ROBOTS_TEXT)
    assert policy.crawl_delay("seowolf") == 2
    assert policy.crawl_delay("anybot") is None
    assert policy.sitemaps == ["https://example.com/sitemap.xml"]


def test_comments_and_case_are_handled() -> None:
    text = "USER-AGENT: *   # every bot\nDISALLOW: /tmp/ # scratch\n"
    assert not allowed(text, "/tmp/file")


def test_missing_robots_allows_and_server_errors_disallow() -> None:
    home = URL("https://example.com/")
    assert policy_from_response(404, b"").is_allowed(home)
    assert not policy_from_response(503, b"").is_allowed(home)
    assert not policy_from_response(429, b"").is_allowed(home)
    assert not policy_from_response(None, b"").is_allowed(home)
    assert policy_from_response(200, b"\xef\xbb\xbfUser-agent: *\nDisallow:\n").is_allowed(home)
