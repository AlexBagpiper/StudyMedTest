"""Add email change verification fields

Revision ID: email_change_001
Revises: split_full_name_001
Create Date: 2026-01-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'email_change_001'
down_revision: Union[str, None] = 'split_full_name_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('pending_email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_change_code', sa.String(6), nullable=True))
    op.add_column('users', sa.Column('email_change_expires', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'email_change_expires')
    op.drop_column('users', 'email_change_code')
    op.drop_column('users', 'pending_email')
