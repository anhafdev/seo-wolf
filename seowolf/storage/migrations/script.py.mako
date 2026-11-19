from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
__author__ = "@anhafxd"

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "op.execute('SELECT 1')"}


def downgrade() -> None:
    ${downgrades if downgrades else "op.execute('SELECT 1')"}
