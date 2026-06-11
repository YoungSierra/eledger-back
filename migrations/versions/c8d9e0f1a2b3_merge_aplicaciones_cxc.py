"""Elimina cxc_recibo_aplicacion y agrega estado a cxc_aplicacion

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cxc_aplicacion",
        sa.Column("estado", sa.String(10), nullable=False,
                  server_default="aplicado"))
    op.create_check_constraint(
        "chk_cxc_app_estado", "cxc_aplicacion",
        "estado IN ('pendiente','aplicado')"
    )
    op.drop_index("idx_recibo_app_recibo", table_name="cxc_recibo_aplicacion")
    op.drop_table("cxc_recibo_aplicacion")


def downgrade():
    op.create_table(
        "cxc_recibo_aplicacion",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recibo_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cxc_documento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("factura_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cxc_documento.id"), nullable=False),
        sa.Column("valor", sa.Numeric(18, 4), nullable=False),
    )
    op.create_index("idx_recibo_app_recibo", "cxc_recibo_aplicacion", ["recibo_id"])
    op.drop_constraint("chk_cxc_app_estado", "cxc_aplicacion")
    op.drop_column("cxc_aplicacion", "estado")
