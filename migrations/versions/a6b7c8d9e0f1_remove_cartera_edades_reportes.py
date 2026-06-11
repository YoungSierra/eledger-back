"""Elimina opción cartera por edades del módulo reportes (duplicado de CxC)

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op

revision = "a6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DELETE FROM adm_permiso_opcion
        WHERE opcion_id = (
            SELECT id FROM adm_opcion
            WHERE codigo = 'cartera'
              AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'reportes')
        )
    """)
    op.execute("""
        DELETE FROM adm_opcion
        WHERE codigo = 'cartera'
          AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'reportes')
    """)


def downgrade():
    op.execute("""
        INSERT INTO adm_opcion (modulo_id, codigo, nombre, ruta, orden, implementada)
        VALUES (
            (SELECT id FROM adm_modulo WHERE codigo = 'reportes'),
            'cartera', 'Cartera por edades', '/dashboard/reportes/cartera', 7, false
        )
    """)
