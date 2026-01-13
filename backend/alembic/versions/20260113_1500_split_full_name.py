"""Split full_name into last_name, first_name, middle_name

Revision ID: split_full_name_001
Revises: f91c8e7e89ed
Create Date: 2026-01-13 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'split_full_name_001'
down_revision: Union[str, None] = 'f91c8e7e89ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем новые колонки
    op.add_column('users', sa.Column('last_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('middle_name', sa.String(100), nullable=True))
    
    # Мигрируем данные из full_name
    # Предполагаем формат "Фамилия Имя Отчество"
    op.execute("""
        UPDATE users 
        SET 
            last_name = SPLIT_PART(full_name, ' ', 1),
            first_name = CASE 
                WHEN POSITION(' ' IN full_name) > 0 
                THEN SPLIT_PART(full_name, ' ', 2) 
                ELSE '' 
            END,
            middle_name = CASE 
                WHEN ARRAY_LENGTH(STRING_TO_ARRAY(full_name, ' '), 1) > 2 
                THEN SPLIT_PART(full_name, ' ', 3)
                ELSE NULL 
            END
    """)
    
    # Устанавливаем NOT NULL для обязательных полей
    op.alter_column('users', 'last_name', nullable=False)
    op.alter_column('users', 'first_name', nullable=False)
    
    # Удаляем старую колонку
    op.drop_column('users', 'full_name')


def downgrade() -> None:
    # Добавляем обратно full_name
    op.add_column('users', sa.Column('full_name', sa.String(255), nullable=True))
    
    # Собираем ФИО обратно
    op.execute("""
        UPDATE users 
        SET full_name = TRIM(
            last_name || ' ' || first_name || 
            CASE WHEN middle_name IS NOT NULL THEN ' ' || middle_name ELSE '' END
        )
    """)
    
    # Устанавливаем NOT NULL
    op.alter_column('users', 'full_name', nullable=False)
    
    # Удаляем новые колонки
    op.drop_column('users', 'middle_name')
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')
