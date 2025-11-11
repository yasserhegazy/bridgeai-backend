"""initial schema

Revision ID: 531baa9737e9
Revises: 
Create Date: 2025-10-18 09:31:06.609637

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '531baa9737e9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Create ENUM types
    user_role = sa.Enum('client', 'ba', name='userrole')
    project_status = sa.Enum('active', 'completed', 'archived', name='projectstatus')
    session_status = sa.Enum('active', 'completed', name='sessionstatus')
    sender_type = sa.Enum('client', 'ai', 'ba', name='sendertype')
    crs_status = sa.Enum('draft', 'under_review', 'approved', 'rejected', name='crsstatus')
    source_type = sa.Enum('crs', 'message', 'comment', 'summary', name='sourcetype')

    user_role.create(bind, checkfirst=True)
    project_status.create(bind, checkfirst=True)
    session_status.create(bind, checkfirst=True)
    sender_type.create(bind, checkfirst=True)
    crs_status.create(bind, checkfirst=True)
    source_type.create(bind, checkfirst=True)

    # Create tables
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('full_name', sa.String(length=256), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('password_hash', sa.String(length=512), nullable=False),
        sa.Column('role', user_role, nullable=True, server_default='client'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', project_status, nullable=True, server_default='active'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', session_status, nullable=True, server_default='active'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=False),
        sa.Column('sender_type', sender_type, nullable=False),
        sa.Column('sender_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'crs_documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary_points', sa.Text(), nullable=True),
        sa.Column('status', crs_status, nullable=True, server_default='draft'),
        sa.Column('version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('crs_id', sa.Integer(), sa.ForeignKey('crs_documents.id'), nullable=False),
        sa.Column('author_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'ai_memory_index',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('source_type', source_type, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('embedding_id', sa.String(length=256), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_ai_memory_index_embedding_id', 'ai_memory_index', ['embedding_id'], unique=True)

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    # Drop indexes and tables in reverse order
    op.drop_index('ix_ai_memory_index_embedding_id', table_name='ai_memory_index')
    op.drop_table('ai_memory_index')

    op.drop_table('comments')

    op.drop_table('crs_documents')

    op.drop_table('messages')

    op.drop_table('sessions')

    op.drop_table('projects')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

    # Drop ENUM types
    user_role = sa.Enum('client', 'ba', name='userrole')
    project_status = sa.Enum('active', 'completed', 'archived', name='projectstatus')
    session_status = sa.Enum('active', 'completed', name='sessionstatus')
    sender_type = sa.Enum('client', 'ai', 'ba', name='sendertype')
    crs_status = sa.Enum('draft', 'under_review', 'approved', 'rejected', name='crsstatus')
    source_type = sa.Enum('crs', 'message', 'comment', 'summary', name='sourcetype')

    source_type.drop(bind, checkfirst=True)
    crs_status.drop(bind, checkfirst=True)
    sender_type.drop(bind, checkfirst=True)
    session_status.drop(bind, checkfirst=True)
    project_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)


