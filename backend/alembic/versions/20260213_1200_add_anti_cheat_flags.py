"""add anti cheat flags

Revision ID: add_anti_cheat_flags
Revises: add_partial_scoring_params
Create Date: 2026-02-13 12:00:00.000000

"""
from typing import Sequence, Union
import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_anti_cheat_flags'
down_revision: Union[str, None] = 'add_partial_scoring_params'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns with default False
    op.add_column('questions', sa.Column('ai_check_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('questions', sa.Column('plagiarism_check_enabled', sa.Boolean(), server_default='false', nullable=False))

    # 2. Migrate existing data from scoring_criteria JSONB if present
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT id, scoring_criteria FROM questions WHERE type::text ILIKE 'text'"))
    questions = res.fetchall()
    
    for q_id, criteria in questions:
        if criteria is None:
            continue
            
        if isinstance(criteria, str):
            try:
                criteria = json.loads(criteria)
            except:
                continue
        
        if not isinstance(criteria, dict):
            continue

        ai_enabled = criteria.pop('ai_check_enabled', False)
        plagiarism_enabled = criteria.pop('plagiarism_check_enabled', False)
        
        if ai_enabled or plagiarism_enabled:
            conn.execute(
                sa.text("UPDATE questions SET ai_check_enabled = :ai, plagiarism_check_enabled = :plag, scoring_criteria = :criteria WHERE id = :id"),
                {
                    "ai": ai_enabled, 
                    "plag": plagiarism_enabled, 
                    "criteria": json.dumps(criteria), 
                    "id": str(q_id)
                }
            )


def downgrade() -> None:
    op.drop_column('questions', 'plagiarism_check_enabled')
    op.drop_column('questions', 'ai_check_enabled')
