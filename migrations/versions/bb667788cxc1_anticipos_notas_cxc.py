"""CxC Fase A — cuenta anticipos de clientes + activar menús notas/anticipos

- cxc_parametro_contable.cuenta_anticipos_id (Anticipos de clientes, 2705)
- Marca implementada=true las opciones notas_cxc, notas_deb_cxc, anticipos_cxc

Revision ID: bb667788cxc1
Revises: ba556677vrt5
Create Date: 2026-07-24
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "bb667788cxc1"
down_revision = "ba556677vrt5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cxc_parametro_contable",
        sa.Column("cuenta_anticipos_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cxc_param_cuenta_anticipos",
        "cxc_parametro_contable", "cnt_cuenta",
        ["cuenta_anticipos_id"], ["id"],
    )
    op.execute("UPDATE adm_opcion SET implementada = true WHERE codigo IN ('notas_cxc', 'notas_deb_cxc', 'anticipos_cxc')")


def downgrade():
    op.execute("UPDATE adm_opcion SET implementada = false WHERE codigo IN ('notas_cxc', 'notas_deb_cxc', 'anticipos_cxc')")
    op.drop_constraint("fk_cxc_param_cuenta_anticipos", "cxc_parametro_contable", type_="foreignkey")
    op.drop_column("cxc_parametro_contable", "cuenta_anticipos_id")
