"""Parámetros de facturación en el concepto (ope_concepto)

Agrega cuenta_ingreso_id y tarifa_iva_id a ope_concepto, para que la factura de
venta contra cotización tome la cuenta de ingreso y el IVA desde el concepto.

Revision ID: zz778899vvww
Revises: yy667788uuvv
Create Date: 2026-07-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "zz778899vvww"
down_revision = "yy667788uuvv"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ope_concepto", sa.Column("cuenta_ingreso_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ope_concepto", sa.Column("tarifa_iva_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_concepto_cuenta_ingreso", "ope_concepto", "cnt_cuenta", ["cuenta_ingreso_id"], ["id"])
    op.create_foreign_key("fk_concepto_tarifa_iva", "ope_concepto", "cnt_tarifa_iva", ["tarifa_iva_id"], ["id"])


def downgrade():
    op.drop_constraint("fk_concepto_tarifa_iva", "ope_concepto", type_="foreignkey")
    op.drop_constraint("fk_concepto_cuenta_ingreso", "ope_concepto", type_="foreignkey")
    op.drop_column("ope_concepto", "tarifa_iva_id")
    op.drop_column("ope_concepto", "cuenta_ingreso_id")
