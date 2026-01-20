"""add pattern column to crs_documents

Revision ID: 99f1e2d3c4b5
Revises: c961cde4f0b0
Create Date: 2026-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99f1e2d3c4b5'
down_revision: Union[str, Sequence[str], None] = 'c961cde4f0b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add pattern column to crs_documents."""
    bind = op.get_bind()
    
    # Create ENUM type for CRS patterns - use a database-specific approach
    # MySQL handles ENUM as a native type
    op.execute("ALTER TABLE crs_documents ADD COLUMN pattern ENUM('iso_iec_ieee_29148', 'ieee_830', 'bakok') NOT NULL DEFAULT 'babok'")


def downgrade() -> None:
    """Downgrade schema - remove pattern column from crs_documents."""
    op.drop_column('crs_documents', 'pattern')
