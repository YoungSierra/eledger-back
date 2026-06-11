"""mawb_totales_campos

Agrega otros_due_agent, otros_due_carrier y total_prepaid a ope_mawb.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-06-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ope_mawb', sa.Column('otros_due_agent', sa.Numeric(18, 4), nullable=True))
    op.add_column('ope_mawb', sa.Column('otros_due_carrier', sa.Numeric(18, 4), nullable=True))
    op.add_column('ope_mawb', sa.Column('total_prepaid', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column('ope_mawb', 'total_prepaid')
    op.drop_column('ope_mawb', 'otros_due_carrier')
    op.drop_column('ope_mawb', 'otros_due_agent')
