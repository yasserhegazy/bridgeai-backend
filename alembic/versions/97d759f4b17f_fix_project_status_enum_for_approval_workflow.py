"""fix_project_status_enum_for_approval_workflow

Revision ID: 97d759f4b17f
Revises: f2f10cbd3092
Create Date: 2025-11-13 12:32:06.368725

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '97d759f4b17f'
down_revision: Union[str, Sequence[str], None] = 'f2f10cbd3092'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Alter the status column to use the new ENUM values
    op.alter_column('projects', 'status',
               existing_type=mysql.ENUM('active', 'completed', 'archived'),
               type_=sa.Enum('pending', 'approved', 'rejected', 'active', 'completed', 'archived', name='projectstatus'),
               existing_nullable=True,
               nullable=False,
               server_default='pending')


def downgrade() -> None:
    """Downgrade schema."""
    # Revert status column to old ENUM values
    op.alter_column('projects', 'status',
               existing_type=sa.Enum('pending', 'approved', 'rejected', 'active', 'completed', 'archived', name='projectstatus'),
               type_=mysql.ENUM('active', 'completed', 'archived'),
               existing_nullable=False,
               nullable=True,
               server_default='active')
