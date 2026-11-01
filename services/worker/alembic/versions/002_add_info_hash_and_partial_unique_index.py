"""add info_hash and partial unique index on active imdb_id

Revision ID: 002_add_info_hash_and_partial_unique_index
Revises: 234da461ab5b
Create Date: 2026-10-31 22:36:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_info_hash_and_partial_unique_index"
down_revision: Union[str, Sequence[str], None] = "234da461ab5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add info_hash and partial unique index on active imdb_id."""
    with op.batch_alter_table("download_jobs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("info_hash", sa.String(length=64), nullable=True)
        )
        batch_op.create_index(
            batch_op.f("ix_download_jobs_info_hash"),
            ["info_hash"],
            unique=False,
        )
        batch_op.create_index(
            "uq_download_jobs_active_imdb_id",
            ["imdb_id"],
            unique=True,
            sqlite_where=sa.text("state NOT IN ('COMPLETED', 'FAILED')"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("download_jobs", schema=None) as batch_op:
        batch_op.drop_index("uq_download_jobs_active_imdb_id")
        batch_op.drop_index(batch_op.f("ix_download_jobs_info_hash"))
        batch_op.drop_column("info_hash")
