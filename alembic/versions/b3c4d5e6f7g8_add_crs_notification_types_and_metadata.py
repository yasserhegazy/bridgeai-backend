"""add_crs_notification_types_and_metadata

Revision ID: b3c4d5e6f7g8
Revises: 3536218ab710
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7g8'
down_revision = '16041c546c69'
branch_labels = None
depends_on = None


def upgrade():
    # Change type column from enum to string to support more notification types
    op.alter_column('notifications', 'type',
                    existing_type=sa.Enum('PROJECT_APPROVAL', 'TEAM_INVITATION', name='notificationtype'),
                    type_=sa.String(50),
                    existing_nullable=False)
    
    # Add meta_data column
    op.add_column('notifications', sa.Column('meta_data', sa.JSON(), nullable=True))


def downgrade():
    # Remove meta_data column
    op.drop_column('notifications', 'meta_data')
    
    # Revert type column back to enum
    op.alter_column('notifications', 'type',
                    existing_type=sa.String(50),
                    type_=sa.Enum('PROJECT_APPROVAL', 'TEAM_INVITATION', name='notificationtype'),
                    existing_nullable=False)
