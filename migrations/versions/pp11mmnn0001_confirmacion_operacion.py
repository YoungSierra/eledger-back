"""Confirmación de operación sobre lo cotizado + conceptos opcionales

Comercial cotiza; operación confirma lo que realmente se ejecutó. Hasta ahora se
facturaba directo contra la cotización, así que un valor mal cotizado o un
servicio que nunca se prestó llegaba tal cual a la factura.

La confirmación va en tabla aparte y no como columnas de `ope_cotizacion_linea`
porque la cotización es un documento comercial ya aprobado y no se muta: queda
el rastro de qué se cotizó contra qué se ejecutó.

`opcional` marca conceptos que pueden o no ejecutarse. Se cotizan con su valor
pero no suman en la sección ni en el total; entran a facturación solo si
operación los confirma.

NO hay backfill deliberadamente: las cotizaciones abiertas se confirman a mano.

Revision ID: pp11mmnn0001
Revises: oo00llmm0001
"""
from alembic import op
import sqlalchemy as sa

revision = "pp11mmnn0001"
down_revision = "oo00llmm0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ope_cotizacion_linea",
        sa.Column("opcional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "ope_confirmacion_linea",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operacion_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ope_operacion.id"), nullable=False),
        sa.Column("cotizacion_linea_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ope_cotizacion_linea.id"), nullable=False),
        sa.Column("confirmado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("base_confirmada", sa.Numeric(18, 4), nullable=False, server_default=sa.text("1")),
        sa.Column("valor_unitario_confirmado", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("costo_unitario_confirmado", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("total_venta_confirmado", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("total_costo_confirmado", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("confirmado_por", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("adm_usuario.id"), nullable=True),
        sa.Column("confirmado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("operacion_id", "cotizacion_linea_id", name="uq_confirmacion_operacion_linea"),
    )
    op.create_index("idx_confirmacion_operacion", "ope_confirmacion_linea", ["operacion_id"])
    op.create_index("idx_confirmacion_linea", "ope_confirmacion_linea", ["cotizacion_linea_id"])


def downgrade() -> None:
    op.drop_index("idx_confirmacion_linea", table_name="ope_confirmacion_linea")
    op.drop_index("idx_confirmacion_operacion", table_name="ope_confirmacion_linea")
    op.drop_table("ope_confirmacion_linea")
    op.drop_column("ope_cotizacion_linea", "opcional")
