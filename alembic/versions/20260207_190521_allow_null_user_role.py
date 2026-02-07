"""allow null user role for post-registration role selection

Revision ID: 20260207_190521
Revises: 20260205_092104
Create Date: 2026-02-07 19:05:21.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260207_190521'
down_revision: Union[str, None] = '20260205_092104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove the server_default='client' from the users.role column.
    This allows new users to have NULL role until they explicitly select one
    via the role selection modal after registration/OAuth login.
    
    Existing users will keep their current roles.
    """
    # Remove server default from role column
    # Note: This does NOT change existing data, only affects new rows
    op.alter_column(
        'users',
        'role',
        existing_type=sa.Enum('client', 'ba', name='userrole'),
        server_default=None,
        nullable=True,
        comment='User role: NULL indicates role not yet selected, must choose client or ba'
    )


def downgrade() -> None:
    """
    Restore the server_default='client' to the users.role column.
    This reverts the migration if needed.
    """
    # Restore server default
    op.alter_column(
        'users',
        'role',
        existing_type=sa.Enum('client', 'ba', name='userrole'),
        server_default='client',
        nullable=True,
        comment=None
    )
