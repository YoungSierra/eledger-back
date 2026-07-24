"""Unidad de medida en el concepto (ope_concepto.um_id)

La UM que se usa al facturar un concepto se administra en el propio concepto.

Revision ID: ab001122wwxx
Revises: zz778899vvww
Create Date: 2026-07-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ab001122wwxx"
down_revision = "zz778899vvww"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ope_concepto", sa.Column("um_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_concepto_um", "ope_concepto", "inv_unidad_medida", ["um_id"], ["id"])


def downgrade():
    op.drop_constraint("fk_concepto_um", "ope_concepto", type_="foreignkey")
    op.drop_column("ope_concepto", "um_id")
