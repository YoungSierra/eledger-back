"""Ocultar el reporte 'Conciliación bancaria' (pendiente de definir con el cliente).

Revision ID: ii44ffgg0001
Revises: hh33eeffban3
Create Date: 2026-07-28
"""
from alembic import op

revision = "ii44ffgg0001"
down_revision = "hh33eeffban3"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE adm_opcion SET activo = false WHERE ruta = '/dashboard/reportes/conciliacion'")


def downgrade():
    op.execute("UPDATE adm_opcion SET activo = true WHERE ruta = '/dashboard/reportes/conciliacion'")
