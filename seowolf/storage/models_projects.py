from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from seowolf.storage.models_base import Base, JsonColumn, utc_now

__author__ = "@anhafxd"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    start_url: Mapped[str] = mapped_column(String(2048))
    settings: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    branding: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    schedule_cron: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
