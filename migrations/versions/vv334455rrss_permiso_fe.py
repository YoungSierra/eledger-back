"""Permisos de la opción Facturación electrónica

La migración uu223344qqrr creó la opción de menú pero no los permisos, así que
no le aparecía a ningún rol — incluido superadmin.

Revision ID: vv334455rrss
Revises: uu223344qqrr
Create Date: 2026-07-15
"""
from alembic import op

revision = "vv334455rrss"
down_revision = "uu223344qqrr"
branch_labels = None
depends_on = None

CODIGO = "admin_facturacion_electronica"


def upgrade():
    # superadmin: todo.
    op.execute(f"""
        INSERT INTO adm_permiso_opcion
            (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_imprimir, puede_autorizar)
        SELECT gen_random_uuid(), r.id, o.id, true, true, true, true, false, false
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'superadmin' AND o.codigo = '{CODIGO}'
          AND NOT EXISTS (
              SELECT 1 FROM adm_permiso_opcion p WHERE p.rol_id = r.id AND p.opcion_id = o.id
          )
    """)
    # administrador: ver y editar, sin borrar. Guarda credenciales de la DIAN;
    # no es una pantalla donde convenga poder eliminar la configuración.
    op.execute(f"""
        INSERT INTO adm_permiso_opcion
            (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_imprimir, puede_autorizar)
        SELECT gen_random_uuid(), r.id, o.id, true, false, true, false, false, false
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'administrador' AND o.codigo = '{CODIGO}'
          AND NOT EXISTS (
              SELECT 1 FROM adm_permiso_opcion p WHERE p.rol_id = r.id AND p.opcion_id = o.id
          )
    """)


def downgrade():
    op.execute(f"""
        DELETE FROM adm_permiso_opcion
        WHERE opcion_id IN (SELECT id FROM adm_opcion WHERE codigo = '{CODIGO}')
    """)
