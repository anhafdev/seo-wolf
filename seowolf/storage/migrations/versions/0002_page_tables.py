from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

__author__ = "@anhafxd"

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_column(name: str) -> sa.Column:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    return sa.Column(name, json_type, nullable=False)


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
        "pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        crawl_reference(),
        required("url", sa.String(4096)),
        required("url_key", sa.String(40)),
        required("final_url", sa.String(4096)),
        optional("status_code", sa.Integer()),
        optional("fetch_error", sa.String(80)),
        optional("content_type", sa.String(200)),
        required("bytes", sa.Integer()),
        optional("response_ms", sa.Integer()),
        optional("http_version", sa.String(20)),
        required("depth", sa.Integer()),
        required("indexable", sa.Boolean()),
        required("indexability_reason", sa.String(40)),
        optional("title", sa.Text()),
        optional("meta_description", sa.Text()),
        optional("h1", sa.Text()),
        optional("canonical", sa.String(4096)),
        optional("robots_meta", sa.String(500)),
        optional("x_robots_tag", sa.String(500)),
        required("word_count", sa.Integer()),
        required("text_ratio", sa.Float()),
        optional("simhash", sa.BigInteger()),
        optional("lang", sa.String(40)),
        required("rendered", sa.Boolean()),
        json_column("raw_vs_rendered_delta"),
        json_column("extracted"),
        json_column("head_data"),
        json_column("response_headers"),
        optional("internal_pagerank", sa.Float()),
        optional("html", sa.Text()),
        required("crawled_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("crawl_id", "url_key", name="uq_pages_crawl_url_key"),
    )
    op.create_index("ix_pages_crawl_status", "pages", ["crawl_id", "status_code"])
    op.create_table(
        "links",
        sa.Column("id", sa.Integer(), primary_key=True),
        crawl_reference(),
        sa.Column(
            "from_page_id",
            sa.Integer(),
            sa.ForeignKey("pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        optional("to_url", sa.String(4096)),
        optional("to_url_key", sa.String(40)),
        required("href", sa.String(4096)),
        required("element", sa.String(20)),
        required("anchor_text", sa.Text()),
        required("rel", sa.String(200)),
        required("is_internal", sa.Boolean()),
        required("nofollow", sa.Boolean()),
        required("position", sa.String(20)),
    )
    op.create_index("ix_links_crawl_to_url_key", "links", ["crawl_id", "to_url_key"])
    op.create_index("ix_links_from_page", "links", ["from_page_id"])
    op.create_table(
        "redirects",
        sa.Column("id", sa.Integer(), primary_key=True),
        crawl_reference(),
        required("source_url", sa.String(4096)),
        required("final_url", sa.String(4096)),
        optional("final_status_code", sa.Integer()),
        required("hop_count", sa.Integer()),
        required("is_loop", sa.Boolean()),
        optional("error", sa.String(80)),
        json_column("chain"),
    )
    op.create_index("ix_redirects_crawl_id", "redirects", ["crawl_id"])


def downgrade() -> None:
    op.drop_table("redirects")
    op.drop_table("links")
    op.drop_table("pages")
