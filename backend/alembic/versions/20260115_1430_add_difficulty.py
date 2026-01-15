"""add difficulty to questions

Revision ID: 20260115_1430_add_difficulty
Revises: 9f63974dc48e
Create Date: 2026-01-15 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260115_1430_add_difficulty'
down_revision = '9f63974dc48e'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем колонку difficulty в таблицу questions
    op.add_column('questions', sa.Column('difficulty', sa.Integer(), nullable=False, server_default='1'))
    op.create_index(op.f('ix_questions_difficulty'), 'questions', ['difficulty'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_questions_difficulty'), table_name='questions')
    op.drop_column('questions', 'difficulty')
