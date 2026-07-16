"""Opción de menú: Facturación electrónica (Administración)

Revision ID: uu223344qqrr
Revises: tt112233ppqq
Create Date: 2026-07-15
"""
from alembic import op

revision = "uu223344qqrr"
down_revision = "tt112233ppqq"
branch_labels = None
depends_on = None

CODIGO = "admin_facturacion_electronica"
RUTA = "/dashboard/administracion/facturacion-electronica"


def upgrade():
    op.execute(f"""
        INSERT INTO adm_opcion (id, modulo_id, codigo, nombre, ruta, orden, implementada, activo)
        SELECT gen_random_uuid(), m.id, '{CODIGO}', 'Facturación electrónica', '{RUTA}', 11, true, true
        FROM adm_modulo m
        WHERE m.codigo = 'administracion'
          AND NOT EXISTS (SELECT 1 FROM adm_opcion o WHERE o.codigo = '{CODIGO}')
    """)


def downgrade():
    op.execute(f"DELETE FROM adm_opcion WHERE codigo = '{CODIGO}'")
