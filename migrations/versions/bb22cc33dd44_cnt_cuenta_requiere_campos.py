"""cnt_cuenta_requiere_campos

Agrega requiere_tercero y requiere_cc a cnt_cuenta.

Revision ID: bb22cc33dd44
Revises: aabb11223344
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'bb22cc33dd44'
down_revision: Union[str, None] = 'aabb11223344'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cnt_cuenta', sa.Column('requiere_tercero', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('cnt_cuenta', sa.Column('requiere_cc', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('cnt_cuenta', 'requiere_cc')
    op.drop_column('cnt_cuenta', 'requiere_tercero')
