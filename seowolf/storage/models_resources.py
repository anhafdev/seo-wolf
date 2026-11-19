from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from seowolf.storage.models_base import Base

__author__ = "@anhafxd"


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawls.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(4096))
    url_key: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(20))
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_url: Mapped[str] = mapped_column(String(4096))
    final_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("crawl_id", "url_key", name="uq_resources_crawl_url_key"),
        Index("ix_resources_crawl_status", "crawl_id", "final_status_code"),
    )


class SitemapFile(Base):
    __tablename__ = "sitemap_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawls.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(4096))
    parent_url: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(20))
    url_count: Mapped[int] = mapped_column(Integer, default=0)
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    gzipped: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)


class SitemapUrl(Base):
    __tablename__ = "sitemap_urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawls.id", ondelete="CASCADE"))
    sitemap_url: Mapped[str] = mapped_column(String(4096))
    loc: Mapped[str] = mapped_column(String(4096))
    normalised_url: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    url_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lastmod: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (Index("ix_sitemap_urls_crawl_url_key", "crawl_id", "url_key"),)
