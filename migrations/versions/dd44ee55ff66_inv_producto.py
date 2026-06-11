"""inv_producto

Revision ID: dd44ee55ff66
Revises: aa11bb22cc33
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'dd44ee55ff66'
down_revision: Union[str, None] = 'aa11bb22cc33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'inv_producto',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('familia_id', sa.UUID(), nullable=True),
        sa.Column('um_base_id', sa.UUID(), nullable=False),
        sa.Column('maneja_inventario', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('maneja_series', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('maneja_lotes', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('tiene_variantes', sa.Boolean(), nullable=False, server_default=sa.false()),
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
        sa.CheckConstraint("tipo IN ('MERCANCIA','SERVICIO','MATERIA_PRIMA','INSUMO')", name='chk_producto_tipo'),
        sa.ForeignKeyConstraint(['familia_id'], ['inv_familia.id']),
        sa.ForeignKeyConstraint(['um_base_id'], ['inv_unidad_medida.id']),
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
    op.create_index('idx_producto_codigo', 'inv_producto', ['codigo'])
    op.create_index('idx_producto_tipo', 'inv_producto', ['tipo'])

    op.create_table(
        'inv_producto_um',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('producto_id', sa.UUID(), nullable=False),
        sa.Column('um_id', sa.UUID(), nullable=False),
        sa.Column('factor', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('es_compra', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('es_venta', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(['producto_id'], ['inv_producto.id']),
        sa.ForeignKeyConstraint(['um_id'], ['inv_unidad_medida.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('producto_id', 'um_id', name='uq_producto_um'),
    )

    # Marcar productos como implementada
    op.execute("UPDATE adm_opcion SET implementada = TRUE WHERE codigo = 'productos'")

    # Permiso superadmin para productos (si faltaba)
    op.execute("""
        INSERT INTO adm_permiso_opcion (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar)
        SELECT gen_random_uuid(), r.id, o.id, TRUE, TRUE, TRUE, TRUE
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'superadmin' AND o.codigo = 'productos'
        AND NOT EXISTS (
            SELECT 1 FROM adm_permiso_opcion p WHERE p.rol_id = r.id AND p.opcion_id = o.id
        )
    """)


def downgrade() -> None:
    op.execute("UPDATE adm_opcion SET implementada = FALSE WHERE codigo = 'productos'")
    op.drop_table('inv_producto_um')
    op.drop_table('inv_producto')
