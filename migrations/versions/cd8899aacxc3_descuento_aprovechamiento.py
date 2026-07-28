"""CxC — cuentas de descuento y aprovechamiento en Parámetros CxC (ajuste en recibo)

Revision ID: cd8899aacxc3
Revises: bc778899cxc2
Create Date: 2026-07-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "cd8899aacxc3"
down_revision = "bc778899cxc2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cxc_parametro_contable",
        sa.Column("cuenta_descuentos_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "cxc_parametro_contable",
        sa.Column("cuenta_aprovechamientos_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cxc_param_descuentos",
        "cxc_parametro_contable", "cnt_cuenta",
        ["cuenta_descuentos_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_cxc_param_aprovechamientos",
        "cxc_parametro_contable", "cnt_cuenta",
        ["cuenta_aprovechamientos_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_cxc_param_aprovechamientos", "cxc_parametro_contable", type_="foreignkey")
    op.drop_constraint("fk_cxc_param_descuentos", "cxc_parametro_contable", type_="foreignkey")
    op.drop_column("cxc_parametro_contable", "cuenta_aprovechamientos_id")
    op.drop_column("cxc_parametro_contable", "cuenta_descuentos_id")
