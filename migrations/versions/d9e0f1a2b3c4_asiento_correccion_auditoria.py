"""Auditoría de correcciones de asientos manuales

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d9e0f1a2b3c4"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cnt_asiento_correccion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asiento_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_asiento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motivo", sa.Text, nullable=False),
        sa.Column("snapshot_lineas", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_cnt_asiento_correccion_asiento_id",
                    "cnt_asiento_correccion", ["asiento_id"])


def downgrade():
    op.drop_table("cnt_asiento_correccion")
