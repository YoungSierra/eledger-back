"""inv_movimiento: agregar campo numero y tipos AJ/TR

Revision ID: qq889900mmnn
Revises: pp778899llmm
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'qq889900mmnn'
down_revision = 'pp778899llmm'
branch_labels = None
depends_on = None


def upgrade():
    # Columna numero en inv_movimiento
    op.add_column('inv_movimiento', sa.Column('numero', sa.String(30), nullable=True))

    # Insertar tipos de documento para ajustes y traslados
    op.execute("""
        INSERT INTO adm_tipo_documento (id, codigo, nombre, modulo, activo)
        SELECT gen_random_uuid(), 'AJ', 'Ajuste de inventario', 'inventario', true
        WHERE NOT EXISTS (SELECT 1 FROM adm_tipo_documento WHERE codigo = 'AJ')
    """)
    op.execute("""
        INSERT INTO adm_tipo_documento (id, codigo, nombre, modulo, activo)
        SELECT gen_random_uuid(), 'TR', 'Traslado de inventario', 'inventario', true
        WHERE NOT EXISTS (SELECT 1 FROM adm_tipo_documento WHERE codigo = 'TR')
    """)

    # Insertar consecutivos iniciales
    op.execute("""
        INSERT INTO adm_consecutivo (id, tipo_documento_id, prefijo, numero_actual, numero_inicio, longitud_minima, activo)
        SELECT gen_random_uuid(), td.id, 'AJ-', 0, 1, 4, true
        FROM adm_tipo_documento td
        WHERE td.codigo = 'AJ'
          AND NOT EXISTS (
            SELECT 1 FROM adm_consecutivo c WHERE c.tipo_documento_id = td.id
          )
    """)
    op.execute("""
        INSERT INTO adm_consecutivo (id, tipo_documento_id, prefijo, numero_actual, numero_inicio, longitud_minima, activo)
        SELECT gen_random_uuid(), td.id, 'TR-', 0, 1, 4, true
        FROM adm_tipo_documento td
        WHERE td.codigo = 'TR'
          AND NOT EXISTS (
            SELECT 1 FROM adm_consecutivo c WHERE c.tipo_documento_id = td.id
          )
    """)


def downgrade():
    op.drop_column('inv_movimiento', 'numero')
