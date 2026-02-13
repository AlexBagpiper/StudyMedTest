"""add_partial_scoring_params

Revision ID: add_partial_scoring_params
Revises: remove_work_fields_001
Create Date: 2026-02-11 12:00:00.000000

"""
from typing import Sequence, Union
import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_partial_scoring_params'
down_revision: Union[str, None] = 'remove_work_fields_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update CV config in system_configs
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT value FROM system_configs WHERE key = 'cv_evaluation_params'"))
    row = res.fetchone()
    
    if row:
        config = row[0]
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except:
                config = {}
        
        if not isinstance(config, dict):
            config = {}
        
        # Add new defaults
        config.setdefault('inclusion_threshold', 0.8)
        config.setdefault('min_coverage_threshold', 0.05)
        config.setdefault('loyalty_factor', 2.0)
        
        conn.execute(
            sa.text("UPDATE system_configs SET value = :val WHERE key = 'cv_evaluation_params'"),
            {"val": json.dumps(config)}
        )

    # 2. Update existing IMAGE_ANNOTATION questions to have allow_partial: false in scoring_criteria
    res = conn.execute(sa.text("SELECT id, scoring_criteria FROM questions WHERE type::text ILIKE 'image_annotation'"))
    questions = res.fetchall()
    
    for q_id, criteria in questions:
        if criteria is None:
            criteria = {}
        elif isinstance(criteria, str):
            try:
                criteria = json.loads(criteria)
            except:
                criteria = {}
            
        if not isinstance(criteria, dict):
            criteria = {}

        if 'allow_partial' not in criteria:
            criteria['allow_partial'] = False
            conn.execute(
                sa.text("UPDATE questions SET scoring_criteria = :criteria WHERE id = :id"),
                {"criteria": json.dumps(criteria), "id": str(q_id)}
            )


def downgrade() -> None:
    pass
