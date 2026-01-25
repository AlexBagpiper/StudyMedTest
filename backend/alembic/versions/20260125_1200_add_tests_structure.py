"""add tests structure column

Revision ID: 20260125_1200
Revises: 20260123_1600
Create Date: 2026-01-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260125_1200'
down_revision: Union[str, None] = '20260123_1600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку structure в таблицу tests
    op.add_column('tests', sa.Column('structure', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Удаляем колонку structure из таблицы tests
    op.drop_column('tests', 'structure')
