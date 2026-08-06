"""Nómina electrónica — tablas nom_periodo, nom_empleado, nom_evento.

Revision ID: kk66hhii0001
Revises: jj55gghh0001
Create Date: 2026-07-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "kk66hhii0001"
down_revision = "jj55gghh0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nom_periodo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.String(30), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="NOMINA"),
        sa.Column("periodo_pago_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_pago_fin", sa.Date(), nullable=False),
        sa.Column("fecha_generacion", sa.Date(), nullable=False),
        sa.Column("periodo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cnt_periodo.id"), nullable=False),
        sa.Column("total_devengado", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_deducciones", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_neto", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="borrador"),
        sa.Column("cune", sa.String(100), nullable=True),
        sa.Column("dian_estado", sa.String(20), nullable=True),
        sa.Column("dian_mensaje", sa.Text(), nullable=True),
        sa.Column("xml_key", sa.String(300), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("numero", name="uq_nom_periodo_numero"),
        sa.CheckConstraint("tipo IN ('NOMINA','AJUSTE')", name="chk_nom_periodo_tipo"),
        sa.CheckConstraint("estado IN ('borrador','generado','enviado','aceptado','rechazado','anulado')", name="chk_nom_periodo_estado"),
    )
    op.create_table(
        "nom_empleado",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("periodo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nom_periodo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orden", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("tipo_documento", sa.String(10), nullable=False, server_default="CC"),
        sa.Column("numero_documento", sa.String(30), nullable=False),
        sa.Column("primer_nombre", sa.String(100), nullable=False),
        sa.Column("otros_nombres", sa.String(100), nullable=True),
        sa.Column("primer_apellido", sa.String(100), nullable=False),
        sa.Column("segundo_apellido", sa.String(100), nullable=True),
        sa.Column("cargo", sa.String(150), nullable=True),
        sa.Column("salario_basico", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("dias_trabajados", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("sueldo", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("auxilio_transporte", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("horas_extra", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("bonificaciones", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("comisiones", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("devengados_extra", postgresql.JSONB, nullable=True),
        sa.Column("salud", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("pension", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("fondo_solidaridad", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("retencion_fuente", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("deducciones_extra", postgresql.JSONB, nullable=True),
        sa.Column("total_devengado", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_deducciones", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("neto", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )
    op.create_index("ix_nom_empleado_periodo", "nom_empleado", ["periodo_id"])
    op.create_table(
        "nom_evento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("periodo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nom_periodo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=True),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("respuesta", postgresql.JSONB, nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_nom_evento_periodo", "nom_evento", ["periodo_id"])


def downgrade():
    op.drop_index("ix_nom_evento_periodo", table_name="nom_evento")
    op.drop_table("nom_evento")
    op.drop_index("ix_nom_empleado_periodo", table_name="nom_empleado")
    op.drop_table("nom_empleado")
    op.drop_table("nom_periodo")
