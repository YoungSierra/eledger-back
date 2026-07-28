"""CxP — notas crédito/débito y anticipos: factura afectada, cuentas de anticipo/
descuento/aprovechamiento y activación de menús.

Revision ID: de99aabbcxp2
Revises: cd8899aacxc3
Create Date: 2026-07-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "de99aabbcxp2"
down_revision = "cd8899aacxc3"
branch_labels = None
depends_on = None


def upgrade():
    # Factura afectada por notas
    op.add_column(
        "cxp_documento",
        sa.Column("factura_afectada_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cxp_doc_factura_afectada",
        "cxp_documento", "cxp_documento",
        ["factura_afectada_id"], ["id"],
    )

    # Cuentas en parámetros CxP
    for col, fk in [
        ("cuenta_anticipos_id", "fk_cxp_param_anticipos"),
        ("cuenta_descuentos_id", "fk_cxp_param_descuentos"),
        ("cuenta_aprovechamientos_id", "fk_cxp_param_aprovechamientos"),
    ]:
        op.add_column("cxp_parametro_contable", sa.Column(col, postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(fk, "cxp_parametro_contable", "cnt_cuenta", [col], ["id"])

    # Activar menús de notas y anticipos CxP
    op.execute(
        "UPDATE adm_opcion SET implementada = true "
        "WHERE ruta IN ('/dashboard/cxp/notas', '/dashboard/cxp/notas-debito', '/dashboard/cxp/anticipos')"
    )


def downgrade():
    op.execute(
        "UPDATE adm_opcion SET implementada = false "
        "WHERE ruta IN ('/dashboard/cxp/notas', '/dashboard/cxp/notas-debito', '/dashboard/cxp/anticipos')"
    )
    for col, fk in [
        ("cuenta_aprovechamientos_id", "fk_cxp_param_aprovechamientos"),
        ("cuenta_descuentos_id", "fk_cxp_param_descuentos"),
        ("cuenta_anticipos_id", "fk_cxp_param_anticipos"),
    ]:
        op.drop_constraint(fk, "cxp_parametro_contable", type_="foreignkey")
        op.drop_column("cxp_parametro_contable", col)
    op.drop_constraint("fk_cxp_doc_factura_afectada", "cxp_documento", type_="foreignkey")
    op.drop_column("cxp_documento", "factura_afectada_id")
