"""ban_banco_config_extracto

Agrega campos de configuración de extracto a ban_banco
y saldo_inicial a ban_cuenta.

Revision ID: cc33dd44ee55
Revises: bb22cc33dd44
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision: str = 'cc33dd44ee55'
down_revision: Union[str, None] = 'bb22cc33dd44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ban_banco — configuración de extracto
    op.add_column('ban_banco', sa.Column('formato', sa.String(length=10), nullable=True))
    op.add_column('ban_banco', sa.Column('mapeo_columnas', pg.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('ban_banco', sa.Column('fila_inicio', sa.SmallInteger(), nullable=True))
    op.add_column('ban_banco', sa.Column('formato_fecha', sa.String(length=20), nullable=True))

    # ban_cuenta — saldo inicial
    op.add_column('ban_cuenta', sa.Column('saldo_inicial', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('ban_cuenta', 'saldo_inicial')
    op.drop_column('ban_banco', 'formato_fecha')
    op.drop_column('ban_banco', 'fila_inicio')
    op.drop_column('ban_banco', 'mapeo_columnas')
    op.drop_column('ban_banco', 'formato')
