"""Bancos — transferencias entre cuentas (ban_transferencia) + tipo documento TRB
+ consecutivo + activación de menú.

Revision ID: ef00bbccban1
Revises: de99aabbcxp2
Create Date: 2026-07-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ef00bbccban1"
down_revision = "de99aabbcxp2"
branch_labels = None
depends_on = None

TD_ID = "932abeab-d7ca-41a2-a8be-b72ce2131cc4"
CONS_ID = "416f2140-ad7f-49d4-9152-094a66a151de"


def upgrade():
    op.create_table(
        "ban_transferencia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.String(30), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("periodo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_periodo.id"), nullable=False),
        sa.Column("cuenta_origen_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ban_cuenta.id"), nullable=False),
        sa.Column("cuenta_destino_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ban_cuenta.id"), nullable=False),
        sa.Column("valor", sa.Numeric(18, 4), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="borrador"),
        sa.Column("asiento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_asiento.id"), nullable=True),
        # AuditMixin
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("numero", name="uq_ban_transf_numero"),
        sa.CheckConstraint("estado IN ('borrador','contabilizado','anulado')", name="chk_ban_transf_estado"),
        sa.CheckConstraint("cuenta_origen_id <> cuenta_destino_id", name="chk_ban_transf_distintas"),
        sa.CheckConstraint("valor > 0", name="chk_ban_transf_valor"),
    )

    # Tipo de documento + consecutivo TRB
    op.execute(
        f"INSERT INTO adm_tipo_documento (id, codigo, nombre, modulo, activo) "
        f"VALUES ('{TD_ID}', 'TRB', 'Transferencia bancaria', 'ban', true) "
        f"ON CONFLICT (codigo) DO NOTHING"
    )
    op.execute(
        f"INSERT INTO adm_consecutivo (id, tipo_documento_id, prefijo, numero_actual, numero_inicio, longitud_minima, activo) "
        f"VALUES ('{CONS_ID}', '{TD_ID}', 'TR', 0, 1, 5, true) "
        f"ON CONFLICT DO NOTHING"
    )

    op.execute(
        "UPDATE adm_opcion SET implementada = true WHERE ruta = '/dashboard/bancos/transferencias'"
    )


def downgrade():
    op.execute("UPDATE adm_opcion SET implementada = false WHERE ruta = '/dashboard/bancos/transferencias'")
    op.execute(f"DELETE FROM adm_consecutivo WHERE id = '{CONS_ID}'")
    op.execute(f"DELETE FROM adm_tipo_documento WHERE id = '{TD_ID}'")
    op.drop_table("ban_transferencia")
