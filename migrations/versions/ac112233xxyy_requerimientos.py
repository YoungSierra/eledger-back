"""Bandeja de requerimientos internos (req_requerimiento, req_mensaje)

Crea solo las tablas. No hay módulo de menú ni permisos: el acceso es
transversal por el icono de campana de la barra superior (cualquier usuario
autenticado).

Revision ID: ac112233xxyy
Revises: ab001122wwxx
Create Date: 2026-07-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ac112233xxyy"
down_revision = "ab001122wwxx"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "req_requerimiento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.String(20), nullable=False, unique=True),
        sa.Column("asunto", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("solicitante_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_usuario.id"), nullable=False),
        sa.Column("asignado_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_usuario.id"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
        sa.Column("prioridad", sa.String(10), nullable=False, server_default="MEDIA"),
        sa.Column("fecha_limite", sa.Date(), nullable=True),
        sa.Column("archivo_nombre", sa.String(255), nullable=True),
        sa.Column("archivo_ruta", sa.String(500), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("estado IN ('PENDIENTE','EN_PROCESO','REVISION','REALIZADO')", name="chk_req_estado"),
        sa.CheckConstraint("prioridad IN ('BAJA','MEDIA','ALTA')", name="chk_req_prioridad"),
    )
    op.create_index("idx_req_asignado", "req_requerimiento", ["asignado_id"])
    op.create_index("idx_req_solicitante", "req_requerimiento", ["solicitante_id"])
    op.create_index("idx_req_estado", "req_requerimiento", ["estado"])

    op.create_table(
        "req_mensaje",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requerimiento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("req_requerimiento.id"), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_usuario.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="COMENTARIO"),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        sa.Column("estado_nuevo", sa.String(20), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tipo IN ('COMENTARIO','CAMBIO_ESTADO')", name="chk_req_msg_tipo"),
    )
    op.create_index("idx_req_msg_requerimiento", "req_mensaje", ["requerimiento_id"])
    # Sin módulo de menú ni permisos: el acceso es transversal por el icono de
    # campana en la barra superior, disponible para cualquier usuario autenticado.


def downgrade():
    op.drop_index("idx_req_msg_requerimiento", table_name="req_mensaje")
    op.drop_table("req_mensaje")
    op.drop_index("idx_req_estado", table_name="req_requerimiento")
    op.drop_index("idx_req_solicitante", table_name="req_requerimiento")
    op.drop_index("idx_req_asignado", table_name="req_requerimiento")
    op.drop_table("req_requerimiento")
