"""add_dashboard_performance_indexes

Revision ID: ae068e1e14c7
Revises: dab2f2a7cbc2
Create Date: 2026-01-29 18:45:08.482324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae068e1e14c7'
down_revision: Union[str, Sequence[str], None] = 'dab2f2a7cbc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add indexes for dashboard statistics queries
    # Index for fetching team projects by status
    op.create_index(
        'idx_project_team_status',
        'projects',
        ['team_id', 'status'],
        unique=False
    )
    
    # Index for fetching project sessions by status
    op.create_index(
        'idx_session_project_status',
        'sessions',
        ['project_id', 'status'],
        unique=False
    )
    
    # Index for fetching CRS documents by project and status
    op.create_index(
        'idx_crs_project_status',
        'crs_documents',
        ['project_id', 'status'],
        unique=False
    )
    
    # Index for fetching recent projects by team (ordered by created_at)
    op.create_index(
        'idx_project_team_created',
        'projects',
        ['team_id', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes in reverse order
    op.drop_index('idx_project_team_created', table_name='projects')
    op.drop_index('idx_crs_project_status', table_name='crs_documents')
    op.drop_index('idx_session_project_status', table_name='sessions')
    op.drop_index('idx_project_team_status', table_name='projects')
