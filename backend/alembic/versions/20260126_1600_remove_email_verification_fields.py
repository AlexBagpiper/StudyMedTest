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
down_revision: Union[str, None] = 'add_tests_structure_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('users')]
    
    if 'email_change_expires' in columns:
        op.drop_column('users', 'email_change_expires')
    if 'email_change_code' in columns:
        op.drop_column('users', 'email_change_code')
    if 'pending_email' in columns:
        op.drop_column('users', 'pending_email')


def downgrade() -> None:
    op.add_column('users', sa.Column('pending_email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_change_code', sa.String(6), nullable=True))
    op.add_column('users', sa.Column('email_change_expires', sa.DateTime(), nullable=True))
