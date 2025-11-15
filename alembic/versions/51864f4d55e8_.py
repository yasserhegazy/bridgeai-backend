"""empty message

Revision ID: 51864f4d55e8
Revises: 97d759f4b17f, d3e4f5g6h7i8
Create Date: 2025-11-15 11:01:35.245818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51864f4d55e8'
down_revision: Union[str, Sequence[str], None] = ('97d759f4b17f', 'd3e4f5g6h7i8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
