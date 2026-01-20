"""add crs_pattern column to sessions

Revision ID: a0b1c2d3e4f5
Revises: 99f1e2d3c4b5
Create Date: 2026-01-20 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, Sequence[str], None] = '99f1e2d3c4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add crs_pattern column to sessions."""
    # Use raw SQL for MySQL ENUM type
    op.execute("ALTER TABLE sessions ADD COLUMN crs_pattern ENUM('iso_iec_ieee_29148', 'ieee_830', 'bakok') NOT NULL DEFAULT 'bakok'")


def downgrade() -> None:
    """Downgrade schema - remove crs_pattern column from sessions."""
    op.drop_column('sessions', 'crs_pattern')
