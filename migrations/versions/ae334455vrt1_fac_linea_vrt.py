"""VRT Fase 2 — marca de valor tercero en la línea de factura de venta

- fac_factura_linea.valor_tercero  (bool, default false)
- fac_factura_linea.proveedor_id   (FK adm_tercero, nullable) — tercero al que se traslada

Revision ID: ae334455vrt1
Revises: ad223344vrt0
Create Date: 2026-07-24
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ae334455vrt1"
down_revision = "ad223344vrt0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "fac_factura_linea",
        sa.Column("valor_tercero", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "fac_factura_linea",
        sa.Column("proveedor_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_fac_linea_proveedor",
        "fac_factura_linea", "adm_tercero",
        ["proveedor_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_fac_linea_proveedor", "fac_factura_linea", type_="foreignkey")
    op.drop_column("fac_factura_linea", "proveedor_id")
    op.drop_column("fac_factura_linea", "valor_tercero")
