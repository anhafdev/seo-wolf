from dataclasses import dataclass, field

from selectolax.lexbor import LexborHTMLParser, LexborNode

__author__ = "@anhafxd"

ROBOTS_META_NAMES = {"robots", "seowolf"}


@dataclass
class HeadTags:
    titles: list[str] = field(default_factory=list)
    meta_descriptions: list[str] = field(default_factory=list)
    robots_meta: list[str] = field(default_factory=list)
    canonicals: list[str] = field(default_factory=list)
    base_href: str | None = None
    lang: str | None = None
    viewport: str | None = None
    charset: str | None = None

    @property
    def title(self) -> str | None:
        return self.titles[0] if self.titles else None

    @property
    def meta_description(self) -> str | None:
        return self.meta_descriptions[0] if self.meta_descriptions else None

    @property
    def canonical(self) -> str | None:
        return self.canonicals[0] if self.canonicals else None


def collapse_spaces(text: str) -> str:
    return " ".join(text.split())


def inside_svg(node: LexborNode) -> bool:
    parent = node.parent
    while parent is not None:
        if parent.tag == "svg":
            return True
        parent = parent.parent
    return False


def attribute(node: LexborNode, name: str) -> str | None:
    value = node.attributes.get(name)
    return value.strip() if isinstance(value, str) else None


def rel_tokens(node: LexborNode) -> set[str]:
    return {token.lower() for token in (attribute(node, "rel") or "").split()}


def read_meta_tags(tree: LexborHTMLParser, tags: HeadTags) -> None:
    for node in tree.css("meta"):
        name = (attribute(node, "name") or "").lower()
        content = attribute(node, "content")
        if node.attributes.get("charset") is not None and tags.charset is None:
            tags.charset = attribute(node, "charset")
        if content is None:
            continue
        if name == "description":
            tags.meta_descriptions.append(collapse_spaces(content))
        elif name in ROBOTS_META_NAMES:
            tags.robots_meta.append(content.lower())
        elif name == "viewport" and tags.viewport is None:
            tags.viewport = content


def extract_head_tags(tree: LexborHTMLParser) -> HeadTags:
    tags = HeadTags()
    tags.titles = [
        collapse_spaces(node.text()) for node in tree.css("title") if not inside_svg(node)
    ]
    read_meta_tags(tree, tags)
    for node in tree.css("link"):
        href = attribute(node, "href")
        if href is not None and "canonical" in rel_tokens(node):
            tags.canonicals.append(href)
    base_node = tree.css_first("base[href]")
    if base_node is not None:
        tags.base_href = attribute(base_node, "href")
    html_node = tree.css_first("html")
    if html_node is not None:
        tags.lang = attribute(html_node, "lang")
    return tags


def robots_directives(meta_values: list[str], header_value: str | None) -> set[str]:
    directives: set[str] = set()
    sources = list(meta_values)
    if header_value:
        sources.append(header_value)
    for source in sources:
        for piece in source.lower().split(","):
            token = piece.strip()
            if ":" in token and not token.startswith(("max-", "unavailable_after")):
                agent, _, token = token.partition(":")
                if agent.strip() not in {"googlebot", "bingbot", "seowolf", "robots"}:
                    continue
                token = token.strip()
            if token == "none":
                directives.update({"noindex", "nofollow"})
            elif token:
                directives.add(token)
    return directives
