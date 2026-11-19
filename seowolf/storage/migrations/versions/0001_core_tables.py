from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

__author__ = "@anhafxd"

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_column(name: str) -> sa.Column:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    return sa.Column(name, json_type, nullable=False)


def crawl_reference() -> sa.Column:
    return sa.Column(
        "crawl_id", sa.Integer(), sa.ForeignKey("crawls.id", ondelete="CASCADE"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("start_url", sa.String(2048), nullable=False),
        json_column("settings"),
        json_column("branding"),
        sa.Column("schedule_cron", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "crawls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        json_column("totals"),
        sa.Column("health_score", sa.Float(), nullable=True),
        json_column("settings_snapshot"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_crawls_project_created", "crawls", ["project_id", "created_at"])
    op.create_table(
        "frontier",
        sa.Column("id", sa.Integer(), primary_key=True),
        crawl_reference(),
        sa.Column("url", sa.String(4096), nullable=False),
        sa.Column("url_key", sa.String(40), nullable=False),
        sa.Column("original_url", sa.String(4096), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("discovered_from", sa.String(4096), nullable=True),
        sa.UniqueConstraint("crawl_id", "url_key", name="uq_frontier_crawl_url_key"),
    )
    op.create_index("ix_frontier_claim", "frontier", ["crawl_id", "state", "priority", "id"])
    op.create_table(
        "robots_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        crawl_reference(),
        sa.Column("origin", sa.String(512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        json_column("sitemaps"),
        sa.Column("blanket_allow", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_robots_files_crawl_id", "robots_files", ["crawl_id"])


def downgrade() -> None:
    op.drop_table("robots_files")
    op.drop_table("frontier")
    op.drop_table("crawls")
    op.drop_table("projects")
