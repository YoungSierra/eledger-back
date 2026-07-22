"""Auditoría de emisión/anulación en documentos operativos (HAWB, MAWB, Manifiesto)

Agrega emitido_por/emitido_en y anulado_por/anulado_en/anulado_motivo a las
tres tablas de documentos operativos, para registrar quién emitió/anuló y cuándo.

Revision ID: ww445566sstt
Revises: vv334455rrss
Create Date: 2026-07-21
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ww445566sstt"
down_revision = "vv334455rrss"
branch_labels = None
depends_on = None

_TABLAS = ("ope_hawb", "ope_mawb", "ope_manifiesto")


def upgrade():
    for t in _TABLAS:
        op.add_column(t, sa.Column("emitido_por", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(t, sa.Column("emitido_en", sa.DateTime(timezone=True), nullable=True))
        op.add_column(t, sa.Column("anulado_por", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(t, sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True))
        op.add_column(t, sa.Column("anulado_motivo", sa.Text(), nullable=True))


def downgrade():
    for t in _TABLAS:
        op.drop_column(t, "anulado_motivo")
        op.drop_column(t, "anulado_en")
        op.drop_column(t, "anulado_por")
        op.drop_column(t, "emitido_en")
        op.drop_column(t, "emitido_por")
