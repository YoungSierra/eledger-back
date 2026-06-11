"""restructure_adm_concepto

Reestructura adm_concepto, adm_concepto_cuenta y adm_concepto_retencion
para referenciar cnt_tarifa_iva, cnt_retencion y cnt_cuenta via FK.

Revision ID: d1e2f3a4b5c6
Revises: b3c4d5e6f7a8
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- adm_concepto_retencion: reemplazar columnas por retencion_id ---
    op.drop_column('adm_concepto_retencion', 'tipo')
    op.drop_column('adm_concepto_retencion', 'descripcion')
    op.drop_column('adm_concepto_retencion', 'base_pct')
    op.drop_column('adm_concepto_retencion', 'porcentaje')
    op.drop_column('adm_concepto_retencion', 'cuenta_id')
    op.drop_column('adm_concepto_retencion', 'aplica_compra')
    op.drop_column('adm_concepto_retencion', 'aplica_venta')
    op.add_column('adm_concepto_retencion',
        sa.Column('retencion_id', sa.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        'fk_concepto_ret_retencion',
        'adm_concepto_retencion', 'cnt_retencion',
        ['retencion_id'], ['id'])

    # --- adm_concepto_cuenta: reemplazar cuenta_codigo por cuenta_id ---
    op.drop_column('adm_concepto_cuenta', 'cuenta_codigo')
    op.add_column('adm_concepto_cuenta',
        sa.Column('cuenta_id', sa.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        'fk_concepto_cuenta_cnt',
        'adm_concepto_cuenta', 'cnt_cuenta',
        ['cuenta_id'], ['id'])

    # --- adm_concepto: quitar campos IVA inline, agregar FK tarifa_iva ---
    op.drop_column('adm_concepto', 'iva_tipo')
    op.drop_column('adm_concepto', 'iva_pct')
    op.drop_column('adm_concepto', 'cuenta_iva_id')
    op.add_column('adm_concepto',
        sa.Column('tarifa_iva_id', sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_concepto_tarifa_iva',
        'adm_concepto', 'cnt_tarifa_iva',
        ['tarifa_iva_id'], ['id'])

    # --- adm_concepto: agregar campos AuditMixin faltantes ---
    op.add_column('adm_concepto',
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True))
    op.add_column('adm_concepto',
        sa.Column('modificado_por', sa.UUID(as_uuid=True), nullable=True))
    op.add_column('adm_concepto',
        sa.Column('eliminado', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_constraint('fk_concepto_tarifa_iva', 'adm_concepto', type_='foreignkey')
    op.drop_column('adm_concepto', 'tarifa_iva_id')
    op.drop_column('adm_concepto', 'modificado_en')
    op.drop_column('adm_concepto', 'modificado_por')
    op.drop_column('adm_concepto', 'eliminado')
    op.add_column('adm_concepto', sa.Column('iva_tipo', sa.String(20), nullable=False, server_default='NINGUNO'))
    op.add_column('adm_concepto', sa.Column('iva_pct', sa.Numeric(8, 4), nullable=False, server_default='0'))
    op.add_column('adm_concepto', sa.Column('cuenta_iva_id', sa.UUID(as_uuid=True), nullable=True))

    op.drop_constraint('fk_concepto_cuenta_cnt', 'adm_concepto_cuenta', type_='foreignkey')
    op.drop_column('adm_concepto_cuenta', 'cuenta_id')
    op.add_column('adm_concepto_cuenta', sa.Column('cuenta_codigo', sa.String(20), nullable=False, server_default=''))

    op.drop_constraint('fk_concepto_ret_retencion', 'adm_concepto_retencion', type_='foreignkey')
    op.drop_column('adm_concepto_retencion', 'retencion_id')
    op.add_column('adm_concepto_retencion', sa.Column('tipo', sa.String(20), nullable=False, server_default='RETEFUENTE'))
    op.add_column('adm_concepto_retencion', sa.Column('descripcion', sa.String(100), nullable=False, server_default=''))
    op.add_column('adm_concepto_retencion', sa.Column('base_pct', sa.Numeric(8, 4), nullable=False, server_default='100'))
    op.add_column('adm_concepto_retencion', sa.Column('porcentaje', sa.Numeric(8, 4), nullable=False, server_default='0'))
    op.add_column('adm_concepto_retencion', sa.Column('cuenta_id', sa.UUID(as_uuid=True), nullable=False, server_default='00000000-0000-0000-0000-000000000000'))
    op.add_column('adm_concepto_retencion', sa.Column('aplica_compra', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('adm_concepto_retencion', sa.Column('aplica_venta', sa.Boolean(), nullable=False, server_default='false'))
