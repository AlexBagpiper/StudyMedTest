"""add teacher applications table

Revision ID: 20260126_1800
Revises: 20260126_1600
Create Date: 2026-01-26 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20260126_1800'
down_revision = 'remove_email_fields_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'teacher_applications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('middle_name', sa.String(100), nullable=True),
        sa.Column('institution', sa.String(255), nullable=True),  # Учебное заведение
        sa.Column('department', sa.String(255), nullable=True),    # Кафедра
        sa.Column('position', sa.String(100), nullable=True),      # Должность
        sa.Column('phone', sa.String(20), nullable=True),          # Телефон
        sa.Column('comment', sa.Text, nullable=True),              # Комментарий от преподавателя
        sa.Column('status', sa.String(20), nullable=False, default='pending', index=True),  # pending, approved, rejected
        sa.Column('admin_comment', sa.Text, nullable=True),        # Комментарий администратора
        sa.Column('reviewed_by', UUID(as_uuid=True), nullable=True),  # ID админа
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
    )


def downgrade() -> None:
    op.drop_table('teacher_applications')
