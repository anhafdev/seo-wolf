from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from seowolf.storage.models_base import Base, JsonColumn, utc_now

__author__ = "@anhafxd"


class Crawl(Base):
    __tablename__ = "crawls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    mode: Mapped[str] = mapped_column(String(20), default="fast")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    totals: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    settings_snapshot: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_crawls_project_created", "project_id", "created_at"),)


class FrontierEntry(Base):
    __tablename__ = "frontier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawls.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(4096))
    url_key: Mapped[str] = mapped_column(String(40))
    original_url: Mapped[str] = mapped_column(String(4096))
    kind: Mapped[str] = mapped_column(String(20), default="page")
    depth: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(20), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    discovered_from: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    __table_args__ = (
        UniqueConstraint("crawl_id", "url_key", name="uq_frontier_crawl_url_key"),
        Index("ix_frontier_claim", "crawl_id", "state", "priority", "id"),
    )


class RobotsFile(Base):
    __tablename__ = "robots_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawls.id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(512))
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body: Mapped[str] = mapped_column(Text, default="")
    sitemaps: Mapped[list[str]] = mapped_column(JsonColumn, default=list)
    blanket_allow: Mapped[bool | None] = mapped_column(nullable=True)
