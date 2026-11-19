import codecs
import re

from selectolax.lexbor import LexborHTMLParser

__author__ = "@anhafxd"

INVISIBLE_TAGS = ["script", "style", "noscript", "template", "svg", "iframe"]
META_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?\s*([a-zA-Z0-9_\-]+)""", re.IGNORECASE)
HEADER_CHARSET = re.compile(r"charset\s*=\s*[\"']?([a-zA-Z0-9_\-]+)", re.IGNORECASE)


def detect_charset(body: bytes, content_type_header: str | None) -> str:
    if body.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if content_type_header:
        header_match = HEADER_CHARSET.search(content_type_header)
        if header_match:
            return header_match.group(1)
    meta_match = META_CHARSET.search(body[:4096])
    if meta_match:
        return meta_match.group(1).decode("ascii", errors="ignore")
    return "utf-8"


def decode_html(body: bytes, content_type_header: str | None) -> str:
    charset = detect_charset(body, content_type_header)
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def visible_text(tree: LexborHTMLParser) -> str:
    tree.strip_tags(INVISIBLE_TAGS)
    container = tree.body or tree.root
    if container is None:
        return ""
    return " ".join(container.text(separator=" ").split())


def count_words(text: str) -> int:
    return sum(1 for token in text.split() if any(character.isalnum() for character in token))


def text_to_html_ratio(text: str, html_length: int) -> float:
    if html_length <= 0:
        return 0.0
    return round(len(text) / html_length, 4)
