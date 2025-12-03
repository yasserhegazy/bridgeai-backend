"""add_name_to_sessions_table

Revision ID: 16041c546c69
Revises: 0c19f2df9037
Create Date: 2025-12-03 13:38:26.399423

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16041c546c69'
down_revision: Union[str, Sequence[str], None] = '0c19f2df9037'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sessions', sa.Column('name', sa.String(255), nullable=False, server_default='Untitled Chat'))
    # Remove server_default after adding the column
    op.alter_column('sessions', 'name', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sessions', 'name')
