"""Agrega ban_cuenta_id a cxc_documento y tabla cxc_recibo_aplicacion

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "b7c8d9e0f1a2"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cxc_documento",
        sa.Column("ban_cuenta_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("ban_cuenta.id"), nullable=True))

    op.create_table(
        "cxc_recibo_aplicacion",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("recibo_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("cxc_documento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("factura_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("cxc_documento.id"), nullable=False),
        sa.Column("valor", sa.Numeric(18, 4), nullable=False),
        sa.CheckConstraint("valor > 0", name="chk_recibo_app_valor"),
    )
    op.create_index("idx_recibo_app_recibo", "cxc_recibo_aplicacion", ["recibo_id"])


def downgrade():
    op.drop_index("idx_recibo_app_recibo", table_name="cxc_recibo_aplicacion")
    op.drop_table("cxc_recibo_aplicacion")
    op.drop_column("cxc_documento", "ban_cuenta_id")
