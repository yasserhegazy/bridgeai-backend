"""remove crs_pattern from sessions table

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-01-20 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove crs_pattern column from sessions.
    
    The CRS pattern should only be stored in crs_documents table.
    Use a JOIN to get the pattern for a specific session via its latest CRS.
    """
    op.drop_column('sessions', 'crs_pattern')


def downgrade() -> None:
    """Downgrade schema - restore crs_pattern column to sessions."""
    # Restore as ENUM column with default value
    op.execute("ALTER TABLE sessions ADD COLUMN crs_pattern ENUM('iso_iec_ieee_29148', 'ieee_830', 'babok') NOT NULL DEFAULT 'babok'")
