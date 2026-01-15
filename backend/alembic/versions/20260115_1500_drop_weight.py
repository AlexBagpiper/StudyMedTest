"""drop weight column from test_questions

Revision ID: 20260115_1500_drop_weight
Revises: 20260115_1430_add_difficulty
Create Date: 2026-01-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260115_1500_drop_weight'
down_revision = '20260115_1430_add_difficulty'
branch_labels = None
depends_on = None


def upgrade():
    # Удаляем колонку weight из таблицы test_questions
    op.drop_column('test_questions', 'weight')


def downgrade():
    op.add_column('test_questions', sa.Column('weight', sa.Integer(), nullable=False, server_default='1'))
