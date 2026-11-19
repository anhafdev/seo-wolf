from dataclasses import dataclass

from selectolax.lexbor import LexborHTMLParser, LexborNode
from yarl import URL

from seowolf.crawler.url_rules import parse_web_url
from seowolf.parsing.head_tags import attribute, collapse_spaces, rel_tokens

__author__ = "@anhafxd"

POSITION_BY_TAG = {"nav": "nav", "header": "header", "footer": "footer", "aside": "aside"}
POSITION_BY_ROLE = {"navigation": "nav", "banner": "header", "contentinfo": "footer"}
RESOURCE_SELECTORS = (
    ("img[src]", "src", "image"),
    ("script[src]", "src", "script"),
    ("link[href]", "href", "stylesheet"),
)


@dataclass(frozen=True)
class ParsedLink:
    href: str
    url: URL | None
    anchor_text: str
    rel: tuple[str, ...]
    position: str
    element: str

    @property
    def nofollow(self) -> bool:
        return "nofollow" in self.rel


def position_of(node: LexborNode) -> str:
    parent = node.parent
    while parent is not None and parent.tag not in {"body", "html"}:
        if parent.tag in POSITION_BY_TAG:
            return POSITION_BY_TAG[parent.tag]
        role = (attribute(parent, "role") or "").lower()
        if role in POSITION_BY_ROLE:
            return POSITION_BY_ROLE[role]
        parent = parent.parent
    return "content"


def anchor_text_of(node: LexborNode) -> str:
    text = collapse_spaces(node.text(separator=" "))
    if text:
        return text
    image = node.css_first("img[alt]")
    if image is not None:
        return collapse_spaces(attribute(image, "alt") or "")
    return collapse_spaces(attribute(node, "aria-label") or attribute(node, "title") or "")


def page_base_url(page_url: URL, base_href: str | None) -> URL:
    if not base_href:
        return page_url
    return parse_web_url(base_href, page_url) or page_url


def extract_links(tree: LexborHTMLParser, base_url: URL) -> list[ParsedLink]:
    links: list[ParsedLink] = []
    for node in tree.css("a[href], area[href]"):
        href = attribute(node, "href") or ""
        if not href or href.startswith("#"):
            continue
        links.append(
            ParsedLink(
                href=href,
                url=parse_web_url(href, base_url),
                anchor_text=anchor_text_of(node),
                rel=tuple(sorted(rel_tokens(node))),
                position=position_of(node),
                element=node.tag or "a",
            )
        )
    return links


def is_stylesheet(node: LexborNode) -> bool:
    return "stylesheet" in rel_tokens(node)


def extract_resources(tree: LexborHTMLParser, base_url: URL) -> list[ParsedLink]:
    resources: list[ParsedLink] = []
    for selector, source_attribute, kind in RESOURCE_SELECTORS:
        for node in tree.css(selector):
            if kind == "stylesheet" and not is_stylesheet(node):
                continue
            href = attribute(node, source_attribute) or ""
            if not href or href.startswith("data:"):
                continue
            resources.append(
                ParsedLink(
                    href=href,
                    url=parse_web_url(href, base_url),
                    anchor_text=(attribute(node, "alt") or "") if kind == "image" else "",
                    rel=(),
                    position=position_of(node),
                    element=kind,
                )
            )
    return resources
