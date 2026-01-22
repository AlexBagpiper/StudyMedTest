"""add is_hidden to submissions

Revision ID: 20260122_1200_add_is_hidden
Revises: 20260115_1500_drop_weight
Create Date: 2026-01-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260122_1200_add_is_hidden'
down_revision = '20260115_1500_drop_weight'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('submissions', sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade():
    op.drop_column('submissions', 'is_hidden')
