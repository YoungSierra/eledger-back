"""Bancos — conciliación: ban_extracto + ban_extracto_linea, activar menú.

Revision ID: gg22ddeeban2
Revises: ff11ccddadj1
Create Date: 2026-07-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "gg22ddeeban2"
down_revision = "ff11ccddadj1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ban_extracto",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ban_cuenta.id"), nullable=False),
        sa.Column("fecha_desde", sa.Date(), nullable=False),
        sa.Column("fecha_hasta", sa.Date(), nullable=False),
        sa.Column("saldo_final", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="abierta"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_table(
        "ban_extracto_linea",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("extracto_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ban_extracto.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.String(300), nullable=False),
        sa.Column("referencia", sa.String(100), nullable=True),
        sa.Column("valor", sa.Numeric(18, 4), nullable=False),
        sa.Column("conciliado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("asiento_linea_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_asiento_linea.id"), nullable=True),
        sa.Column("conciliado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("conciliado_por", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_ban_extracto_linea_extracto", "ban_extracto_linea", ["extracto_id"])
    op.execute("UPDATE adm_opcion SET implementada = true WHERE ruta = '/dashboard/bancos/conciliacion'")


def downgrade():
    op.execute("UPDATE adm_opcion SET implementada = false WHERE ruta = '/dashboard/bancos/conciliacion'")
    op.drop_index("ix_ban_extracto_linea_extracto", table_name="ban_extracto_linea")
    op.drop_table("ban_extracto_linea")
    op.drop_table("ban_extracto")
