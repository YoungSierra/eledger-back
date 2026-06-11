"""inv_familia

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'inv_familia',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('cuenta_inventario_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_costo_ventas_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_ingreso_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_devolucion_venta_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_devolucion_compra_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_ajuste_entrada_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_ajuste_salida_id', sa.UUID(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', sa.UUID(), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['cuenta_inventario_id'], ['cnt_cuenta.id']),
        sa.ForeignKeyConstraint(['cuenta_costo_ventas_id'], ['cnt_cuenta.id']),
        sa.ForeignKeyConstraint(['cuenta_ingreso_id'], ['cnt_cuenta.id']),
        sa.ForeignKeyConstraint(['cuenta_devolucion_venta_id'], ['cnt_cuenta.id']),
        sa.ForeignKeyConstraint(['cuenta_devolucion_compra_id'], ['cnt_cuenta.id']),
        sa.ForeignKeyConstraint(['cuenta_ajuste_entrada_id'], ['cnt_cuenta.id']),
        sa.ForeignKeyConstraint(['cuenta_ajuste_salida_id'], ['cnt_cuenta.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo'),
    )

    # Agregar opción de menú
    op.execute("""
        INSERT INTO adm_opcion (id, modulo_id, codigo, nombre, ruta, orden, implementada, activo)
        SELECT gen_random_uuid(), m.id, 'familias', 'Familias',
               '/dashboard/inventario/familias', 3, TRUE, TRUE
        FROM adm_modulo m WHERE m.codigo = 'inventario'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM adm_opcion WHERE codigo = 'familias'")
    op.drop_table('inv_familia')
