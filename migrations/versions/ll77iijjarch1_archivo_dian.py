"""Archivo propio de documentos electrónicos (XML/PDF) + número fiscal del PTH

La DIAN exige al emisor conservar los documentos electrónicos 5 años, pero el
PTH (Factus) solo los mantiene disponibles mientras el paquete esté vigente. Se
agregan las llaves de almacenamiento propio y el número fiscal que asigna el PTH
cuando es él quien administra la numeración.

Revision ID: ll77iijj0001
Revises: kk66hhii0001
"""
from alembic import op
import sqlalchemy as sa

revision = "ll77iijj0001"
down_revision = "kk66hhii0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fac_factura", sa.Column("numero_dian", sa.String(length=60), nullable=True))
    op.add_column("fac_factura", sa.Column("xml_key", sa.String(length=300), nullable=True))
    op.add_column("fac_factura", sa.Column("pdf_key", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("fac_factura", "pdf_key")
    op.drop_column("fac_factura", "xml_key")
    op.drop_column("fac_factura", "numero_dian")
