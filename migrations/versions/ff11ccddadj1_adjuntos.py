"""Adjuntos genéricos (adm_adjunto)

Revision ID: ff11ccddadj1
Revises: ef00bbccban1
Create Date: 2026-07-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff11ccddadj1"
down_revision = "ef00bbccban1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "adm_adjunto",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entidad", sa.String(50), nullable=False),
        sa.Column("entidad_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre_archivo", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(400), nullable=False),
        sa.Column("content_type", sa.String(150), nullable=True),
        sa.Column("tamano", sa.BigInteger(), nullable=True),
        sa.Column("descripcion", sa.String(255), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("subido_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subido_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_adm_adjunto_entidad", "adm_adjunto", ["entidad", "entidad_id"])


def downgrade():
    op.drop_index("ix_adm_adjunto_entidad", table_name="adm_adjunto")
    op.drop_table("adm_adjunto")
