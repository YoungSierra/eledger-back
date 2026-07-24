"""VRT Fase 5 — opción de menú del panel de Valores recibidos para terceros

Revision ID: ba556677vrt5
Revises: ae334455vrt1
Create Date: 2026-07-24
"""
from alembic import op

revision = "ba556677vrt5"
down_revision = "ae334455vrt1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        INSERT INTO adm_opcion (id, modulo_id, codigo, nombre, ruta, orden, implementada, activo)
        SELECT gen_random_uuid(), m.id, 'valores_terceros', 'Valores recibidos para terceros',
               '/dashboard/cxp/valores-terceros', 8, true, true
        FROM adm_modulo m
        WHERE m.codigo = 'cxp'
          AND NOT EXISTS (SELECT 1 FROM adm_opcion WHERE codigo = 'valores_terceros')
    """)
    op.execute("""
        INSERT INTO adm_permiso_opcion (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_autorizar)
        SELECT gen_random_uuid(), r.id, o.id, true, false, false, false, false
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre IN ('superadmin', 'contador', 'administrador') AND o.codigo = 'valores_terceros'
          AND NOT EXISTS (SELECT 1 FROM adm_permiso_opcion p WHERE p.rol_id = r.id AND p.opcion_id = o.id)
    """)


def downgrade():
    op.execute("DELETE FROM adm_permiso_opcion WHERE opcion_id IN (SELECT id FROM adm_opcion WHERE codigo = 'valores_terceros')")
    op.execute("DELETE FROM adm_opcion WHERE codigo = 'valores_terceros'")
