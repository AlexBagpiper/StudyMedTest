"""add tests structure column

Revision ID: 20260125_1200_add_tests_structure
Revises: 20260123_1600_add_system_configs
Create Date: 2026-01-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260125_1200_add_tests_structure'
down_revision = '20260123_1600_add_system_configs'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем колонку structure в таблицу tests
    op.add_column('tests', sa.Column('structure', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Удаляем колонку structure из таблицы tests
    op.drop_column('tests', 'structure')
