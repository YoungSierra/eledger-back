"""Mueve opción nómina electrónica de administración a contabilidad

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE adm_opcion
        SET modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'contabilidad'),
            ruta      = '/dashboard/contabilidad/nomina-electronica',
            orden     = 5
        WHERE codigo = 'nomina_electronica'
          AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'administracion')
    """)


def downgrade():
    op.execute("""
        UPDATE adm_opcion
        SET modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'administracion'),
            ruta      = '/dashboard/administracion/nomina-electronica',
            orden     = 6
        WHERE codigo = 'nomina_electronica'
          AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'contabilidad')
    """)
