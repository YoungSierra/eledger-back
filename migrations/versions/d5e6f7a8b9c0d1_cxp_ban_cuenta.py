"""cxp_documento: agregar ban_cuenta_id

Revision ID: d5e6f7a8b9c0d1
Revises: c4d5e6f7a8b9c0
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd5e6f7a8b9c0d1'
down_revision = 'c4d5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cxp_documento',
        sa.Column('ban_cuenta_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_cxp_ban_cuenta', 'cxp_documento',
        'ban_cuenta', ['ban_cuenta_id'], ['id']
    )
    # Marcar comprobantes en el menú
    op.execute("UPDATE adm_opcion SET implementada = true WHERE codigo = 'comprobantes'")
    op.execute("""
        INSERT INTO adm_permiso_opcion (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_autorizar)
        SELECT gen_random_uuid(), r.id, o.id, true, true, true, true, true
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'superadmin' AND o.codigo = 'comprobantes'
          AND NOT EXISTS (
              SELECT 1 FROM adm_permiso_opcion p WHERE p.rol_id = r.id AND p.opcion_id = o.id
          )
    """)


def downgrade():
    op.drop_constraint('fk_cxp_ban_cuenta', 'cxp_documento', type_='foreignkey')
    op.drop_column('cxp_documento', 'ban_cuenta_id')
