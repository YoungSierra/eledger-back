"""inv_unidad_medida

Revision ID: aa11bb22cc33
Revises: a2b3c4d5e6f7
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'aa11bb22cc33'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'inv_unidad_medida',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo'),
    )

    # Opción de menú
    op.execute("""
        INSERT INTO adm_opcion (id, modulo_id, codigo, nombre, ruta, orden, implementada, activo)
        SELECT gen_random_uuid(), m.id, 'unidades_medida', 'Unidades de medida',
               '/dashboard/inventario/unidades-medida', 5, TRUE, TRUE
        FROM adm_modulo m WHERE m.codigo = 'inventario'
        ON CONFLICT DO NOTHING
    """)

    # Permisos superadmin
    op.execute("""
        INSERT INTO adm_permiso_opcion (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar)
        SELECT gen_random_uuid(), r.id, o.id, TRUE, TRUE, TRUE, TRUE
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'superadmin' AND o.codigo = 'unidades_medida'
        ON CONFLICT DO NOTHING
    """)

    # Seeds básicos
    op.execute("""
        INSERT INTO inv_unidad_medida (id, codigo, nombre, activo) VALUES
        (gen_random_uuid(), 'UND',  'Unidad',           TRUE),
        (gen_random_uuid(), 'KG',   'Kilogramo',        TRUE),
        (gen_random_uuid(), 'GR',   'Gramo',            TRUE),
        (gen_random_uuid(), 'LT',   'Litro',            TRUE),
        (gen_random_uuid(), 'ML',   'Mililitro',        TRUE),
        (gen_random_uuid(), 'MTS',  'Metro',            TRUE),
        (gen_random_uuid(), 'CM',   'Centímetro',       TRUE),
        (gen_random_uuid(), 'M2',   'Metro cuadrado',   TRUE),
        (gen_random_uuid(), 'M3',   'Metro cúbico',     TRUE),
        (gen_random_uuid(), 'CAJA', 'Caja',             TRUE),
        (gen_random_uuid(), 'PAR',  'Par',              TRUE),
        (gen_random_uuid(), 'DOC',  'Docena',           TRUE),
        (gen_random_uuid(), 'GLN',  'Galón',            TRUE),
        (gen_random_uuid(), 'TON',  'Tonelada',         TRUE),
        (gen_random_uuid(), 'HRS',  'Hora',             TRUE)
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM adm_permiso_opcion WHERE opcion_id IN (SELECT id FROM adm_opcion WHERE codigo = 'unidades_medida')")
    op.execute("DELETE FROM adm_opcion WHERE codigo = 'unidades_medida'")
    op.drop_table('inv_unidad_medida')
