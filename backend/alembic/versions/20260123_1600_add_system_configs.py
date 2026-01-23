"""add system_configs table

Revision ID: 20260123_1600_add_system_configs
Revises: 20260122_1200_add_is_hidden
Create Date: 2026-01-23 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260123_1600_add_system_configs'
down_revision = '20260122_1200_add_is_hidden'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_configs_key'), 'system_configs', ['key'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_system_configs_key'), table_name='system_configs')
    op.drop_table('system_configs')
