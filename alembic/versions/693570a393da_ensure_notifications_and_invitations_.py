"""ensure_notifications_and_invitations_tables

Revision ID: 693570a393da
Revises: 0c19f2df9037
Create Date: 2025-11-29 19:51:36.995792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '693570a393da'
down_revision: Union[str, Sequence[str], None] = '0c19f2df9037'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - ensure notifications and invitations tables exist."""
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create invitations table if it doesn't exist
    if 'invitations' not in existing_tables:
        op.create_table('invitations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('team_id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('role', sa.Enum('owner', 'admin', 'member', name='teamrole'), nullable=False),
            sa.Column('token', sa.String(length=255), nullable=False),
            sa.Column('status', sa.Enum('pending', 'accepted', 'declined', name='invitationstatus'), nullable=False),
            sa.Column('invited_by', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('token')
        )
        op.create_index(op.f('ix_invitations_email'), 'invitations', ['email'], unique=False)
        op.create_index(op.f('ix_invitations_id'), 'invitations', ['id'], unique=False)
        op.create_index(op.f('ix_invitations_team_id'), 'invitations', ['team_id'], unique=False)
    
    # Create notifications table if it doesn't exist
    if 'notifications' not in existing_tables:
        op.create_table('notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('type', sa.Enum('PROJECT_APPROVAL', 'TEAM_INVITATION', name='notificationtype'), nullable=False),
            sa.Column('reference_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('message', sa.String(length=500), nullable=False),
            sa.Column('is_read', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
        op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - this is a safety migration, downgrade does nothing."""
    # We don't drop tables on downgrade to prevent accidental data loss
    pass
