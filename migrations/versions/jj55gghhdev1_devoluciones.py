"""Devoluciones en ventas — cuentas de devolución + tablas fac_devolucion, activar menú.

Revision ID: jj55gghh0001
Revises: ii44ffgg0001
Create Date: 2026-07-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "jj55gghh0001"
down_revision = "ii44ffgg0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ope_concepto", sa.Column("cuenta_devolucion_venta_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_cuenta.id"), nullable=True))
    op.add_column("cxc_parametro_contable", sa.Column("cuenta_devolucion_venta_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_cuenta.id"), nullable=True))

    op.create_table(
        "fac_devolucion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.String(30), nullable=False),
        sa.Column("factura_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fac_factura.id"), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("motivo", sa.String(300), nullable=False),
        sa.Column("concepto_dian", sa.String(5), nullable=True),
        sa.Column("periodo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_periodo.id"), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=False),
        sa.Column("moneda_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_moneda.id"), nullable=False),
        sa.Column("trm", sa.Numeric(18, 6), nullable=True),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_iva", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="borrador"),
        sa.Column("asiento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_asiento.id"), nullable=True),
        sa.Column("cxc_documento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cxc_documento.id"), nullable=True),
        sa.Column("cune", sa.String(100), nullable=True),
        sa.Column("dian_estado", sa.String(20), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("numero", name="uq_fac_devolucion_numero"),
        sa.CheckConstraint("estado IN ('borrador','contabilizado','anulado')", name="chk_fac_devolucion_estado"),
    )
    op.create_table(
        "fac_devolucion_linea",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("devolucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fac_devolucion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("factura_linea_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fac_factura_linea.id"), nullable=False),
        sa.Column("orden", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("producto_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inv_producto.id"), nullable=True),
        sa.Column("descripcion", sa.String(300), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(18, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False),
        sa.Column("iva_tipo", sa.String(20), nullable=False, server_default="NINGUNO"),
        sa.Column("iva_pct", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("total_iva", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False),
        sa.Column("cuenta_devolucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_cuenta.id"), nullable=True),
        sa.Column("cuenta_iva_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_cuenta.id"), nullable=True),
        sa.Column("centro_costo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_centro_costo.id"), nullable=True),
    )
    op.create_index("ix_fac_devolucion_linea_dev", "fac_devolucion_linea", ["devolucion_id"])
    op.execute("UPDATE adm_opcion SET implementada = true, activo = true WHERE ruta = '/dashboard/facturacion/devoluciones'")


def downgrade():
    op.execute("UPDATE adm_opcion SET implementada = false WHERE ruta = '/dashboard/facturacion/devoluciones'")
    op.drop_index("ix_fac_devolucion_linea_dev", table_name="fac_devolucion_linea")
    op.drop_table("fac_devolucion_linea")
    op.drop_table("fac_devolucion")
    op.drop_column("cxc_parametro_contable", "cuenta_devolucion_venta_id")
    op.drop_column("ope_concepto", "cuenta_devolucion_venta_id")
