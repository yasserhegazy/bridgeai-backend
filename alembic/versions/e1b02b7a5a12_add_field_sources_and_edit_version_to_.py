"""add_field_sources_and_edit_version_to_crs

Revision ID: e1b02b7a5a12
Revises: c961cde4f0b0
Create Date: 2026-01-22 16:14:42.778739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1b02b7a5a12'
down_revision: Union[str, Sequence[str], None] = 'c961cde4f0b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add field_sources column
    op.add_column('crs_documents', sa.Column('field_sources', sa.Text(), nullable=True))
    
    # Add edit_version column for optimistic locking
    op.add_column('crs_documents', sa.Column('edit_version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove added columns
    op.drop_column('crs_documents', 'edit_version')
    op.drop_column('crs_documents', 'field_sources')
