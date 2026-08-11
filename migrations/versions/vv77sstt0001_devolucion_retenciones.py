"""La devolución en ventas reversa retenciones, en proporción a lo devuelto

Hasta ahora la nota crédito de devolución reversaba subtotal e IVA pero fijaba
`total_retenciones = 0`. La retención es un anticipo de impuesto que el cliente
ya declaró a nombre nuestro: si no se reversa, el saldo de "retenciones a favor"
queda inflado y no cuadra con el certificado que el cliente emite al cierre.

Regla acordada con el usuario: **proporcional**. Si se devuelve el 40% de la
factura se reversa el 40% de cada retención. La proporción se toma sobre el
subtotal, que es la base sobre la que se calcularon.

Las retenciones reversadas se guardan en tabla propia, no se recalculan al
vuelo: la nota crédito es un documento fiscal y debe poder reimprimirse igual
dentro de dos años aunque la tarifa del concepto haya cambiado.

`fac_devolucion.total` pasa a ser NETO (subtotal + IVA − retenciones), igual que
`fac_factura.total`. No hay datos que ajustar: no existe ninguna devolución
registrada todavía.

Revision ID: vv77sstt0001
Revises: uu66rrss0001
"""
from alembic import op
import sqlalchemy as sa

revision = "vv77sstt0001"
down_revision = "uu66rrss0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fac_devolucion",
        sa.Column("total_retenciones", sa.Numeric(18, 4), nullable=False,
                  server_default=sa.text("0")),
    )
    op.create_table(
        "fac_devolucion_retencion",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("devolucion_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fac_devolucion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("concepto", sa.String(100), nullable=False),
        sa.Column("base", sa.Numeric(18, 4), nullable=False),
        sa.Column("porcentaje", sa.Numeric(8, 4), nullable=False),
        sa.Column("valor", sa.Numeric(18, 4), nullable=False),
        sa.Column("cuenta_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_cuenta.id"), nullable=False),
        sa.CheckConstraint("tipo IN ('RETEFUENTE','RETEICA','RETEIVA')",
                           name="chk_fac_dev_ret_tipo"),
    )
    op.create_index("idx_fac_dev_ret_devolucion", "fac_devolucion_retencion", ["devolucion_id"])


def downgrade() -> None:
    op.drop_index("idx_fac_dev_ret_devolucion", table_name="fac_devolucion_retencion")
    op.drop_table("fac_devolucion_retencion")
    op.drop_column("fac_devolucion", "total_retenciones")
