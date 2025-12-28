"""merge_crs_and_notifications_migrations

Revision ID: 98e4ce3892b6
Revises: 93c7feaf3e69, b3c4d5e6f7g8
Create Date: 2025-12-28 22:58:57.813933

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98e4ce3892b6'
down_revision: Union[str, Sequence[str], None] = ('93c7feaf3e69', 'b3c4d5e6f7g8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
