"""inv_remision

Revision ID: rr990011nnoo
Revises: qq889900mmnn
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "rr990011nnoo"
down_revision = "qq889900mmnn"
branch_labels = None
depends_on = None


def upgrade():
    # inv_remision
    op.create_table(
        "inv_remision",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("numero", sa.String(30), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("periodo_id", pg.UUID(as_uuid=True), sa.ForeignKey("cnt_periodo.id"), nullable=False),
        sa.Column("cliente_id", pg.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=False),
        sa.Column("bodega_id", pg.UUID(as_uuid=True), sa.ForeignKey("inv_bodega.id"), nullable=False),
        sa.Column("cotizacion_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="borrador"),
        sa.Column("movimiento_id", pg.UUID(as_uuid=True), sa.ForeignKey("inv_movimiento.id"), nullable=True),
        sa.Column("asiento_id", pg.UUID(as_uuid=True), sa.ForeignKey("cnt_asiento.id"), nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("creado_por", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", pg.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("numero", name="uq_inv_remision_numero"),
        sa.CheckConstraint("estado IN ('borrador','despachada','facturada','anulada')", name="chk_inv_remision_estado"),
    )
    op.create_index("idx_inv_remision_cliente", "inv_remision", ["cliente_id"])
    op.create_index("idx_inv_remision_fecha", "inv_remision", ["fecha"])

    # inv_remision_linea
    op.create_table(
        "inv_remision_linea",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("remision_id", pg.UUID(as_uuid=True), sa.ForeignKey("inv_remision.id"), nullable=False),
        sa.Column("producto_id", pg.UUID(as_uuid=True), sa.ForeignKey("inv_producto.id"), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("um_id", pg.UUID(as_uuid=True), sa.ForeignKey("inv_unidad_medida.id"), nullable=False),
        sa.Column("cantidad_base", sa.Numeric(18, 4), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.CheckConstraint("cantidad > 0", name="chk_inv_remision_linea_cantidad"),
    )
    op.create_index("idx_inv_remision_linea_remision", "inv_remision_linea", ["remision_id"])

    # fac_factura_remision — tabla de vínculo factura ↔ remisiones
    op.create_table(
        "fac_factura_remision",
        sa.Column("factura_id", pg.UUID(as_uuid=True), sa.ForeignKey("fac_factura.id"), nullable=False),
        sa.Column("remision_id", pg.UUID(as_uuid=True), sa.ForeignKey("inv_remision.id"), nullable=False),
        sa.PrimaryKeyConstraint("factura_id", "remision_id"),
    )

    # bodega_id en fac_factura (para facturas directas sin remisión)
    op.add_column("fac_factura", sa.Column("bodega_id", pg.UUID(as_uuid=True), sa.ForeignKey("inv_bodega.id"), nullable=True))

    # remision_linea_id en fac_factura_linea (trazabilidad)
    op.add_column("fac_factura_linea", sa.Column("remision_linea_id", pg.UUID(as_uuid=True), sa.ForeignKey("inv_remision_linea.id"), nullable=True))

    # tipo_documento REM ya existe — solo verificamos que el consecutivo esté
    # (no insertamos nada, el usuario ya creó REM)


def downgrade():
    op.drop_column("fac_factura_linea", "remision_linea_id")
    op.drop_column("fac_factura", "bodega_id")
    op.drop_table("fac_factura_remision")
    op.drop_table("inv_remision_linea")
    op.drop_table("inv_remision")
