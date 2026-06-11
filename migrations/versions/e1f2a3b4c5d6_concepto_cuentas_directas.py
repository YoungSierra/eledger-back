"""concepto_cuentas_directas

Reemplaza adm_concepto_cuenta por dos FK directas en adm_concepto:
cuenta_gasto_id (débito) y cuenta_cxp_id (crédito).

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('adm_concepto',
        sa.Column('cuenta_gasto_id', sa.UUID(as_uuid=True), nullable=True))
    op.add_column('adm_concepto',
        sa.Column('cuenta_cxp_id', sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_concepto_cuenta_gasto', 'adm_concepto', 'cnt_cuenta',
        ['cuenta_gasto_id'], ['id'])
    op.create_foreign_key(
        'fk_concepto_cuenta_cxp', 'adm_concepto', 'cnt_cuenta',
        ['cuenta_cxp_id'], ['id'])
    op.drop_table('adm_concepto_cuenta')


def downgrade() -> None:
    op.create_table(
        'adm_concepto_cuenta',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('concepto_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('cuenta_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tipo_movimiento', sa.String(10), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['concepto_id'], ['adm_concepto.id'], name='fk_concepto_cuenta_cnt'),
        sa.ForeignKeyConstraint(['cuenta_id'], ['cnt_cuenta.id']),
    )
    op.drop_constraint('fk_concepto_cuenta_cxp', 'adm_concepto', type_='foreignkey')
    op.drop_constraint('fk_concepto_cuenta_gasto', 'adm_concepto', type_='foreignkey')
    op.drop_column('adm_concepto', 'cuenta_cxp_id')
    op.drop_column('adm_concepto', 'cuenta_gasto_id')
