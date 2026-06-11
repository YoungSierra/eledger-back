"""cxp: marcar saldos_cxp como implementada

Revision ID: c4d5e6f7a8b9c0
Revises: b3c4d5e6f7a8b9
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op

revision = 'c4d5e6f7a8b9c0'
down_revision = 'b3c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE adm_opcion SET implementada = true WHERE codigo = 'saldos_cxp'")
    op.execute("""
        INSERT INTO adm_permiso_opcion (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_autorizar)
        SELECT gen_random_uuid(), r.id, o.id, true, true, true, true, true
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'superadmin' AND o.codigo = 'saldos_cxp'
          AND NOT EXISTS (
              SELECT 1 FROM adm_permiso_opcion p WHERE p.rol_id = r.id AND p.opcion_id = o.id
          )
    """)


def downgrade():
    op.execute("UPDATE adm_opcion SET implementada = false WHERE codigo = 'saldos_cxp'")
