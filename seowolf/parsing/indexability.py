from dataclasses import dataclass

__author__ = "@anhafxd"


@dataclass(frozen=True)
class IndexabilityInput:
    blocked_by_robots: bool
    fetch_error: str | None
    status_code: int | None
    is_html: bool
    directives: frozenset[str]
    page_url: str
    canonical_url: str | None


def judge_indexability(facts: IndexabilityInput) -> tuple[bool, str]:
    if facts.blocked_by_robots:
        return False, "blocked_by_robots"
    if facts.fetch_error or facts.status_code is None:
        return False, "fetch_error"
    if 300 <= facts.status_code < 400:
        return False, "redirect"
    if 400 <= facts.status_code < 500:
        return False, "client_error"
    if facts.status_code >= 500:
        return False, "server_error"
    if facts.status_code != 200:
        return False, "non_200"
    if not facts.is_html:
        return False, "non_html"
    if "noindex" in facts.directives:
        return False, "noindex"
    if facts.canonical_url and facts.canonical_url != facts.page_url:
        return False, "canonicalised"
    return True, "indexable"
