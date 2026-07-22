"""Facturación de venta contra cotización (Fase B) — enlaces y saldo

- fac_factura.cotizacion_id (FK→ope_cotizacion): una factura pertenece a una cotización.
- fac_factura_linea.cotizacion_linea_id (FK→ope_cotizacion_linea) + monto_cotizacion
  (monto facturado en la moneda nativa de la cotización, para el saldo).

Revision ID: yy667788uuvv
Revises: xx556677ttuu
Create Date: 2026-07-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "yy667788uuvv"
down_revision = "xx556677ttuu"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("fac_factura", sa.Column("cotizacion_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_factura_cotizacion", "fac_factura", "ope_cotizacion", ["cotizacion_id"], ["id"])
    op.create_index("idx_factura_cotizacion", "fac_factura", ["cotizacion_id"])

    op.add_column("fac_factura_linea", sa.Column("cotizacion_linea_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("fac_factura_linea", sa.Column("monto_cotizacion", sa.Numeric(18, 4), nullable=True))
    op.create_foreign_key("fk_factura_linea_cotizacion_linea", "fac_factura_linea", "ope_cotizacion_linea", ["cotizacion_linea_id"], ["id"])
    op.create_index("idx_factura_linea_cotizacion_linea", "fac_factura_linea", ["cotizacion_linea_id"])


def downgrade():
    op.drop_index("idx_factura_linea_cotizacion_linea", table_name="fac_factura_linea")
    op.drop_constraint("fk_factura_linea_cotizacion_linea", "fac_factura_linea", type_="foreignkey")
    op.drop_column("fac_factura_linea", "monto_cotizacion")
    op.drop_column("fac_factura_linea", "cotizacion_linea_id")

    op.drop_index("idx_factura_cotizacion", table_name="fac_factura")
    op.drop_constraint("fk_factura_cotizacion", "fac_factura", type_="foreignkey")
    op.drop_column("fac_factura", "cotizacion_id")
