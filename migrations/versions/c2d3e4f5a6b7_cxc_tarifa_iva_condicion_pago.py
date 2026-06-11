"""cxc_documento: tarifa_iva_id y condicion_pago_id

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cxc_documento",
        sa.Column("tarifa_iva_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_tarifa_iva.id"), nullable=True))
    op.add_column("cxc_documento",
        sa.Column("condicion_pago_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("adm_condicion_pago.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("cxc_documento", "condicion_pago_id")
    op.drop_column("cxc_documento", "tarifa_iva_id")
