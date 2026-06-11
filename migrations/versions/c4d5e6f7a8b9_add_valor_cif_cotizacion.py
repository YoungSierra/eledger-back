"""add valor_cif to ope_cotizacion

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-06-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ope_cotizacion', sa.Column('valor_cif', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column('ope_cotizacion', 'valor_cif')
