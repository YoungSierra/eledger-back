"""hawb_mawb_campos_completos

Agrega todos los campos necesarios para imprimir HAWB y MAWB
en formato IATA AWB fiel al documento real de Universal Cargo.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── OPE_HAWB — nuevos campos ─────────────────────────────────────────────

    op.add_column('ope_hawb', sa.Column('mawb_id', sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_hawb_mawb', 'ope_hawb', 'ope_mawb', ['mawb_id'], ['id'])
    op.create_index('idx_hawb_mawb', 'ope_hawb', ['mawb_id'])

    op.add_column('ope_hawb', sa.Column('shipper_account', sa.String(50), nullable=True))
    op.add_column('ope_hawb', sa.Column('consignee_account', sa.String(50), nullable=True))
    op.add_column('ope_hawb', sa.Column('agent_iata_code', sa.String(20), nullable=True))
    op.add_column('ope_hawb', sa.Column('agent_account_no', sa.String(50), nullable=True))

    op.add_column('ope_hawb', sa.Column('tipo_pago_flete', sa.String(5), nullable=False, server_default='PPD'))
    op.add_column('ope_hawb', sa.Column('tipo_pago_otros', sa.String(5), nullable=False, server_default='PPD'))
    op.add_column('ope_hawb', sa.Column('moneda', sa.String(3), nullable=False, server_default='USD'))
    op.add_column('ope_hawb', sa.Column('valor_declarado_transporte', sa.String(50), nullable=False, server_default='NVD'))
    op.add_column('ope_hawb', sa.Column('valor_declarado_aduana', sa.String(50), nullable=False, server_default='NVD'))
    op.add_column('ope_hawb', sa.Column('monto_seguro', sa.String(50), nullable=True))
    op.add_column('ope_hawb', sa.Column('info_manejo', sa.Text(), nullable=True))
    op.add_column('ope_hawb', sa.Column('clase_tarifa', sa.String(10), nullable=True))
    op.add_column('ope_hawb', sa.Column('tarifa', sa.String(50), nullable=True))
    op.add_column('ope_hawb', sa.Column('total_carga', sa.String(50), nullable=True))
    op.add_column('ope_hawb', sa.Column('cargo_peso', sa.String(50), nullable=True))
    op.add_column('ope_hawb', sa.Column('cargo_valuacion', sa.String(50), nullable=True))
    op.add_column('ope_hawb', sa.Column('tax', sa.String(50), nullable=True))
    op.add_column('ope_hawb', sa.Column('otros_cargos', sa.Text(), nullable=True))

    op.create_check_constraint('chk_hawb_tipo_pago_flete', 'ope_hawb', "tipo_pago_flete IN ('PPD','COLL')")
    op.create_check_constraint('chk_hawb_tipo_pago_otros', 'ope_hawb', "tipo_pago_otros IN ('PPD','COLL')")

    # ── OPE_MAWB — nuevos campos ─────────────────────────────────────────────

    op.add_column('ope_mawb', sa.Column('prefix', sa.String(10), nullable=True))
    op.add_column('ope_mawb', sa.Column('consignee_id', sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_mawb_consignee', 'ope_mawb', 'adm_tercero', ['consignee_id'], ['id'])

    op.add_column('ope_mawb', sa.Column('shipper_account', sa.String(50), nullable=True))
    op.add_column('ope_mawb', sa.Column('consignee_account', sa.String(50), nullable=True))
    op.add_column('ope_mawb', sa.Column('trm', sa.Numeric(18, 4), nullable=True))
    op.add_column('ope_mawb', sa.Column('agent_iata_code', sa.String(20), nullable=True))
    op.add_column('ope_mawb', sa.Column('agent_account_no', sa.String(50), nullable=True))

    op.add_column('ope_mawb', sa.Column('tipo_pago_flete', sa.String(5), nullable=False, server_default='PPD'))
    op.add_column('ope_mawb', sa.Column('tipo_pago_otros', sa.String(5), nullable=False, server_default='PPD'))
    op.add_column('ope_mawb', sa.Column('valor_declarado_transporte', sa.String(50), nullable=False, server_default='NVD'))
    op.add_column('ope_mawb', sa.Column('valor_declarado_aduana', sa.String(50), nullable=False, server_default='NVD'))
    op.add_column('ope_mawb', sa.Column('monto_seguro', sa.String(50), nullable=True))
    op.add_column('ope_mawb', sa.Column('info_manejo', sa.Text(), nullable=True))
    op.add_column('ope_mawb', sa.Column('clase_tarifa', sa.String(10), nullable=True))
    op.add_column('ope_mawb', sa.Column('tarifa_por_kg', sa.Numeric(18, 4), nullable=True))
    op.add_column('ope_mawb', sa.Column('dimensiones', sa.Text(), nullable=True))
    op.add_column('ope_mawb', sa.Column('fsc', sa.Numeric(18, 4), nullable=True))
    op.add_column('ope_mawb', sa.Column('due_carrier', sa.Numeric(18, 4), nullable=True))
    op.add_column('ope_mawb', sa.Column('cargo_valuacion', sa.String(50), nullable=True))
    op.add_column('ope_mawb', sa.Column('tax', sa.String(50), nullable=True))

    op.create_check_constraint('chk_mawb_tipo_pago_flete', 'ope_mawb', "tipo_pago_flete IN ('PPD','COLL')")
    op.create_check_constraint('chk_mawb_tipo_pago_otros', 'ope_mawb', "tipo_pago_otros IN ('PPD','COLL')")


def downgrade() -> None:

    # MAWB
    op.drop_constraint('chk_mawb_tipo_pago_otros', 'ope_mawb', type_='check')
    op.drop_constraint('chk_mawb_tipo_pago_flete', 'ope_mawb', type_='check')
    for col in ['tax', 'cargo_valuacion', 'due_carrier', 'fsc', 'dimensiones',
                'tarifa_por_kg', 'clase_tarifa', 'info_manejo', 'monto_seguro',
                'valor_declarado_aduana', 'valor_declarado_transporte',
                'tipo_pago_otros', 'tipo_pago_flete', 'agent_account_no',
                'agent_iata_code', 'trm', 'consignee_account', 'shipper_account',
                'prefix']:
        op.drop_column('ope_mawb', col)
    op.drop_constraint('fk_mawb_consignee', 'ope_mawb', type_='foreignkey')
    op.drop_column('ope_mawb', 'consignee_id')

    # HAWB
    op.drop_constraint('chk_hawb_tipo_pago_otros', 'ope_hawb', type_='check')
    op.drop_constraint('chk_hawb_tipo_pago_flete', 'ope_hawb', type_='check')
    for col in ['otros_cargos', 'tax', 'cargo_valuacion', 'cargo_peso',
                'total_carga', 'tarifa', 'clase_tarifa', 'info_manejo',
                'monto_seguro', 'valor_declarado_aduana', 'valor_declarado_transporte',
                'moneda', 'tipo_pago_otros', 'tipo_pago_flete',
                'agent_account_no', 'agent_iata_code',
                'consignee_account', 'shipper_account']:
        op.drop_column('ope_hawb', col)
    op.drop_index('idx_hawb_mawb', table_name='ope_hawb')
    op.drop_constraint('fk_hawb_mawb', 'ope_hawb', type_='foreignkey')
    op.drop_column('ope_hawb', 'mawb_id')
