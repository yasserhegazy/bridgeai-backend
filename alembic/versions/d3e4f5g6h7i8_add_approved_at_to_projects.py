"""
Add approved_at column to projects table

Revision ID: d3e4f5g6h7i8
Revises: f2f10cbd3092
Create Date: 2025-11-15 12:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd3e4f5g6h7i8'
down_revision = 'f2f10cbd3092'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('projects', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column('projects', 'approved_at')