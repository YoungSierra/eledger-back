"""Ocultar la opción de menú 'Extractos' (cubierta por Conciliación).

Revision ID: hh33eeffban3
Revises: gg22ddeeban2
Create Date: 2026-07-28
"""
from alembic import op

revision = "hh33eeffban3"
down_revision = "gg22ddeeban2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE adm_opcion SET activo = false WHERE ruta = '/dashboard/bancos/extractos'")


def downgrade():
    op.execute("UPDATE adm_opcion SET activo = true WHERE ruta = '/dashboard/bancos/extractos'")
