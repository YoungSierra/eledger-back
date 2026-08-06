"""Retenciones parametrizadas en el concepto operativo

Hasta ahora las retenciones de la factura de venta se capturaban a mano. En una
factura de 13 líneas con dos tarifas distintas (4% servicios, 1% transporte) eso
es lento y propenso a error. El concepto ya parametriza la tarifa de IVA; ahora
también la de retención.

Es tabla puente y no un solo campo porque retefuente y reteICA conviven sobre la
misma base. Mismo patrón que `adm_concepto_retencion` para conceptos de compras.

Revision ID: oo00llmm0001
Revises: nn99kkll0001
"""
from alembic import op
import sqlalchemy as sa

revision = "oo00llmm0001"
down_revision = "nn99kkll0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ope_concepto_retencion",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("concepto_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ope_concepto.id", ondelete="CASCADE"), nullable=False),
        sa.Column("retencion_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_retencion.id"), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("concepto_id", "retencion_id", name="uq_ope_concepto_retencion"),
    )
    op.create_index("idx_ope_concepto_retencion", "ope_concepto_retencion", ["concepto_id"])


def downgrade() -> None:
    op.drop_index("idx_ope_concepto_retencion", table_name="ope_concepto_retencion")
    op.drop_table("ope_concepto_retencion")
