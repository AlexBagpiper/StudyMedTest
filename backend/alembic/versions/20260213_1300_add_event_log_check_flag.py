"""add event log check flag

Revision ID: add_event_log_check_flag
Revises: add_anti_cheat_flags
Create Date: 2026-02-13 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_event_log_check_flag'
down_revision: Union[str, None] = 'add_anti_cheat_flags'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('event_log_check_enabled', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('questions', 'event_log_check_enabled')
