"""merge pattern and field_sources branches

Revision ID: cf5bc0b34108
Revises: e1b02b7a5a12, b1c2d3e4f5a6
Create Date: 2026-01-22 22:40:25.368084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf5bc0b34108'
down_revision: Union[str, Sequence[str], None] = ('e1b02b7a5a12', 'b1c2d3e4f5a6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
