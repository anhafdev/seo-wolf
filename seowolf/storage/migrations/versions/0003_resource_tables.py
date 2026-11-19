from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

__author__ = "@anhafxd"

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def crawl_reference() -> sa.Column:
    return sa.Column(
        "crawl_id", sa.Integer(), sa.ForeignKey("crawls.id", ondelete="CASCADE"), nullable=False
    )


def optional(name: str, column_type: sa.types.TypeEngine) -> sa.Column:
    return sa.Column(name, column_type, nullable=True)


def required(name: str, column_type: sa.types.TypeEngine) -> sa.Column:
    return sa.Column(name, column_type, nullable=False)


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        crawl_reference(),
        required("url", sa.String(4096)),
        required("url_key", sa.String(40)),
        required("kind", sa.String(20)),
        optional("status_code", sa.Integer()),
        required("final_url", sa.String(4096)),
        optional("final_status_code", sa.Integer()),
        optional("content_type", sa.String(200)),
        optional("bytes", sa.Integer()),
        optional("response_ms", sa.Integer()),
        optional("error", sa.String(80)),
        required("is_internal", sa.Boolean()),
        sa.UniqueConstraint("crawl_id", "url_key", name="uq_resources_crawl_url_key"),
    )
    op.create_index("ix_resources_crawl_status", "resources", ["crawl_id", "final_status_code"])
    op.create_table(
        "sitemap_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        crawl_reference(),
        required("url", sa.String(4096)),
        optional("parent_url", sa.String(4096)),
        optional("status_code", sa.Integer()),
        required("kind", sa.String(20)),
        required("url_count", sa.Integer()),
        required("byte_size", sa.Integer()),
        required("gzipped", sa.Boolean()),
        optional("error", sa.String(300)),
    )
    op.create_index("ix_sitemap_files_crawl_id", "sitemap_files", ["crawl_id"])
    op.create_table(
        "sitemap_urls",
        sa.Column("id", sa.Integer(), primary_key=True),
        crawl_reference(),
        required("sitemap_url", sa.String(4096)),
        required("loc", sa.String(4096)),
        optional("normalised_url", sa.String(4096)),
        optional("url_key", sa.String(40)),
        optional("lastmod", sa.String(64)),
    )
    op.create_index("ix_sitemap_urls_crawl_url_key", "sitemap_urls", ["crawl_id", "url_key"])


def downgrade() -> None:
    op.drop_table("sitemap_urls")
    op.drop_table("sitemap_files")
    op.drop_table("resources")
