"""add_invitations_table

Revision ID: 237afc01f63d
Revises: 97d759f4b17f
Create Date: 2025-11-17 23:40:39.996772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '237afc01f63d'
down_revision: Union[str, Sequence[str], None] = '97d759f4b17f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add invitations table for team invitations."""
    op.create_table(
        'invitations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('email', sa.String(256), nullable=False, index=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('invited_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column(
            'status',
            sa.Enum('pending', 'accepted', 'expired', 'canceled', name='invitationstatus'),
            nullable=False,
            server_default='pending'
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove invitations table."""
    op.drop_table('invitations')
