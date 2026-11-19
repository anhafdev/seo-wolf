from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from seowolf.storage.models_base import Base, JsonColumn, utc_now

__author__ = "@anhafxd"


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawls.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(4096))
    url_key: Mapped[str] = mapped_column(String(40))
    final_url: Mapped[str] = mapped_column(String(4096))
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetch_error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    indexable: Mapped[bool] = mapped_column(Boolean, default=False)
    indexability_reason: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    h1: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    robots_meta: Mapped[str | None] = mapped_column(String(500), nullable=True)
    x_robots_tag: Mapped[str | None] = mapped_column(String(500), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    text_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    simhash: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    lang: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rendered: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_vs_rendered_delta: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    extracted: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    head_data: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    response_headers: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    internal_pagerank: Mapped[float | None] = mapped_column(Float, nullable=True)
    html: Mapped[str | None] = mapped_column(Text, nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint("crawl_id", "url_key", name="uq_pages_crawl_url_key"),
        Index("ix_pages_crawl_status", "crawl_id", "status_code"),
    )


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawls.id", ondelete="CASCADE"))
    from_page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"))
    to_url: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    to_url_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    href: Mapped[str] = mapped_column(String(4096))
    element: Mapped[str] = mapped_column(String(20), default="a")
    anchor_text: Mapped[str] = mapped_column(Text, default="")
    rel: Mapped[str] = mapped_column(String(200), default="")
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    nofollow: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[str] = mapped_column(String(20), default="content")

    __table_args__ = (
        Index("ix_links_crawl_to_url_key", "crawl_id", "to_url_key"),
        Index("ix_links_from_page", "from_page_id"),
    )


class Redirect(Base):
    __tablename__ = "redirects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawls.id", ondelete="CASCADE"), index=True)
    source_url: Mapped[str] = mapped_column(String(4096))
    final_url: Mapped[str] = mapped_column(String(4096))
    final_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hop_count: Mapped[int] = mapped_column(Integer, default=0)
    is_loop: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    chain: Mapped[list[dict[str, Any]]] = mapped_column(JsonColumn, default=list)
