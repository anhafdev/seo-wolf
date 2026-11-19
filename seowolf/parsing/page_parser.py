from dataclasses import dataclass, field

from selectolax.lexbor import LexborHTMLParser
from yarl import URL

from seowolf.parsing.content import count_words, text_to_html_ratio, visible_text
from seowolf.parsing.head_tags import HeadTags, collapse_spaces, extract_head_tags
from seowolf.parsing.links import ParsedLink, extract_links, extract_resources, page_base_url

__author__ = "@anhafxd"


@dataclass
class ParsedPage:
    head: HeadTags
    h1s: list[str] = field(default_factory=list)
    links: list[ParsedLink] = field(default_factory=list)
    resources: list[ParsedLink] = field(default_factory=list)
    word_count: int = 0
    text_ratio: float = 0.0

    @property
    def h1(self) -> str | None:
        return self.h1s[0] if self.h1s else None


def parse_page(html: str, page_url: URL) -> ParsedPage:
    tree = LexborHTMLParser(html)
    head = extract_head_tags(tree)
    base_url = page_base_url(page_url, head.base_href)
    parsed = ParsedPage(
        head=head,
        h1s=[collapse_spaces(node.text(separator=" ")) for node in tree.css("h1")],
        links=extract_links(tree, base_url),
        resources=extract_resources(tree, base_url),
    )
    text = visible_text(tree)
    parsed.word_count = count_words(text)
    parsed.text_ratio = text_to_html_ratio(text, len(html))
    return parsed
