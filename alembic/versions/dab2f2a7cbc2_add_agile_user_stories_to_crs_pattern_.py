"""add_agile_user_stories_to_crs_pattern_enum

Revision ID: dab2f2a7cbc2
Revises: 9671358ce69b
Create Date: 2026-01-24 17:53:24.312730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dab2f2a7cbc2'
down_revision: Union[str, Sequence[str], None] = '9671358ce69b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add agile_user_stories to CRSPattern enum."""
    # MySQL: Alter the ENUM type to include the new value
    op.execute(
        "ALTER TABLE crs_documents MODIFY COLUMN pattern "
        "ENUM('iso_iec_ieee_29148', 'ieee_830', 'babok', 'agile_user_stories') "
        "DEFAULT 'babok'"
    )


def downgrade() -> None:
    """Remove agile_user_stories from CRSPattern enum."""
    # First, update any rows using agile_user_stories to babok
    op.execute(
        "UPDATE crs_documents SET pattern = 'babok' "
        "WHERE pattern = 'agile_user_stories'"
    )
    
    # Then alter the ENUM to remove the value
    op.execute(
        "ALTER TABLE crs_documents MODIFY COLUMN pattern "
        "ENUM('iso_iec_ieee_29148', 'ieee_830', 'babok') "
        "DEFAULT 'babok'"
    )
