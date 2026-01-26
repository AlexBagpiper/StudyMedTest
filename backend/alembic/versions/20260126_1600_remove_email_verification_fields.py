"""Remove email verification fields from users table

Revision ID: remove_email_fields_001
Revises: 9f63974dc48e
Create Date: 2026-01-26 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_email_fields_001'
down_revision: Union[str, None] = '20260125_1200_add_tests_structure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('users', 'email_change_expires')
    op.drop_column('users', 'email_change_code')
    op.drop_column('users', 'pending_email')


def downgrade() -> None:
    op.add_column('users', sa.Column('pending_email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_change_code', sa.String(6), nullable=True))
    op.add_column('users', sa.Column('email_change_expires', sa.DateTime(), nullable=True))
