"""fac_factura: tablas de facturación de venta

Revision ID: jj112233eeff
Revises: ii001122ddee
Create Date: 2026-06-10 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from alembic import op

revision: str = 'jj112233eeff'
down_revision: Union[str, None] = 'ii001122ddee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fac_factura',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('numero', sa.String(30), nullable=False),
        sa.Column('fecha', sa.Date, nullable=False),
        sa.Column('fecha_vencimiento', sa.Date, nullable=False),
        sa.Column('periodo_id', pg.UUID(as_uuid=True), sa.ForeignKey('cnt_periodo.id'), nullable=False),
        sa.Column('cliente_id', pg.UUID(as_uuid=True), sa.ForeignKey('adm_tercero.id'), nullable=False),
        sa.Column('moneda_id', pg.UUID(as_uuid=True), sa.ForeignKey('adm_moneda.id'), nullable=False),
        sa.Column('trm', sa.Numeric(18, 6), nullable=True),
        sa.Column('condicion_pago_id', pg.UUID(as_uuid=True), sa.ForeignKey('adm_condicion_pago.id'), nullable=True),
        sa.Column('subtotal', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total_descuentos', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total_iva', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total_retenciones', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('notas', sa.Text, nullable=True),
        sa.Column('estado', sa.String(20), nullable=False, server_default='borrador'),
        sa.Column('asiento_id', pg.UUID(as_uuid=True), sa.ForeignKey('cnt_asiento.id'), nullable=True),
        sa.Column('asiento_modificado_manual', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('cxc_documento_id', pg.UUID(as_uuid=True), sa.ForeignKey('cxc_documento.id'), nullable=True),
        sa.Column('cufe', sa.String(200), nullable=True),
        sa.Column('fecha_dian', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activo', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('creado_por', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', pg.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint('numero', name='uq_fac_factura_numero'),
        sa.CheckConstraint("estado IN ('borrador','contabilizada','anulada')", name='chk_fac_estado'),
    )
    op.create_index('idx_fac_factura_cliente', 'fac_factura', ['cliente_id'])
    op.create_index('idx_fac_factura_fecha', 'fac_factura', ['fecha'])
    op.create_index('idx_fac_factura_estado', 'fac_factura', ['estado'])

    op.create_table(
        'fac_factura_linea',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('factura_id', pg.UUID(as_uuid=True), sa.ForeignKey('fac_factura.id'), nullable=False),
        sa.Column('producto_id', pg.UUID(as_uuid=True), sa.ForeignKey('inv_producto.id'), nullable=True),
        sa.Column('descripcion', sa.String(300), nullable=False),
        sa.Column('cantidad', sa.Numeric(18, 4), nullable=False),
        sa.Column('um_id', pg.UUID(as_uuid=True), sa.ForeignKey('inv_unidad_medida.id'), nullable=True),
        sa.Column('precio_unitario', sa.Numeric(18, 4), nullable=False),
        sa.Column('descuento_pct', sa.Numeric(8, 4), nullable=False, server_default='0'),
        sa.Column('descuento_valor', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('subtotal', sa.Numeric(18, 4), nullable=False),
        sa.Column('iva_tipo', sa.String(20), nullable=False, server_default='NINGUNO'),
        sa.Column('iva_pct', sa.Numeric(8, 4), nullable=False, server_default='0'),
        sa.Column('total_iva', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('cuenta_iva_id', pg.UUID(as_uuid=True), sa.ForeignKey('cnt_cuenta.id'), nullable=True),
        sa.Column('total', sa.Numeric(18, 4), nullable=False),
        sa.Column('cuenta_ingreso_id', pg.UUID(as_uuid=True), sa.ForeignKey('cnt_cuenta.id'), nullable=True),
        sa.Column('orden', sa.SmallInteger, nullable=False, server_default='1'),
        sa.CheckConstraint('cantidad > 0', name='chk_fac_linea_cantidad'),
        sa.CheckConstraint("iva_tipo IN ('GRAVADO_19','GRAVADO_5','EXCLUIDO','EXENTO','INC','NINGUNO')", name='chk_fac_linea_iva_tipo'),
    )
    op.create_index('idx_fac_linea_factura', 'fac_factura_linea', ['factura_id'])

    op.create_table(
        'fac_factura_retencion',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('factura_id', pg.UUID(as_uuid=True), sa.ForeignKey('fac_factura.id'), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('concepto', sa.String(100), nullable=False),
        sa.Column('base', sa.Numeric(18, 4), nullable=False),
        sa.Column('porcentaje', sa.Numeric(8, 4), nullable=False),
        sa.Column('valor', sa.Numeric(18, 4), nullable=False),
        sa.Column('cuenta_id', pg.UUID(as_uuid=True), sa.ForeignKey('cnt_cuenta.id'), nullable=False),
        sa.CheckConstraint("tipo IN ('RETEFUENTE','RETEICA','RETEIVA')", name='chk_fac_ret_tipo'),
    )
    op.create_index('idx_fac_retencion_factura', 'fac_factura_retencion', ['factura_id'])

    # Marcar la opción de menú como implementada
    op.execute("""
        UPDATE adm_opcion SET implementada = true
        WHERE codigo = 'facturas_fac'
    """)


def downgrade() -> None:
    op.drop_table('fac_factura_retencion')
    op.drop_table('fac_factura_linea')
    op.drop_table('fac_factura')
    op.execute("UPDATE adm_opcion SET implementada = false WHERE codigo = 'facturas_fac'")
