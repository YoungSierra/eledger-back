"""inv_tipo_producto

Renombra cnt_parametro_contable a inv_tipo_producto.
Cambia inv_producto.tipo VARCHAR a tipo_id UUID FK.

Revision ID: aabb11223344
Revises: ff778899aabb
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'aabb11223344'
down_revision: Union[str, None] = 'ff778899aabb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Eliminar tablas antiguas (sin datos aún)
    op.drop_table('inv_producto_um')
    op.drop_table('inv_producto')
    op.drop_table('cnt_parametro_contable')

    # 2. Crear inv_tipo_producto
    op.create_table(
        'inv_tipo_producto',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('maneja_inventario', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('cuenta_inventario_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_costo_ventas_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_ingreso_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_devolucion_venta_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_devolucion_compra_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_ajuste_entrada_id', sa.UUID(), nullable=True),
        sa.Column('cuenta_ajuste_salida_id', sa.UUID(), nullable=True),
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

    # 3. Sembrar 4 tipos
    op.execute("""
        INSERT INTO inv_tipo_producto (id, codigo, nombre, maneja_inventario) VALUES
        (gen_random_uuid(), 'MERCANCIA',    'Mercancía',    TRUE),
        (gen_random_uuid(), 'SERVICIO',     'Servicio',     FALSE),
        (gen_random_uuid(), 'MATERIA_PRIMA','Materia prima', TRUE),
        (gen_random_uuid(), 'INSUMO',       'Insumo',       TRUE)
    """)

    # 4. Recrear inv_producto con tipo_id FK
    op.create_table(
        'inv_producto',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('tipo_id', sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(['tipo_id'], ['inv_tipo_producto.id']),
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
    op.create_index('idx_producto_tipo', 'inv_producto', ['tipo_id'])

    # 5. Recrear inv_producto_um
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

    # 6. Menú: quitar de contabilidad, agregar a inventario
    op.execute("DELETE FROM adm_permiso_opcion WHERE opcion_id IN (SELECT id FROM adm_opcion WHERE codigo = 'parametros_contables')")
    op.execute("DELETE FROM adm_opcion WHERE codigo = 'parametros_contables'")

    op.execute("""
        INSERT INTO adm_opcion (id, modulo_id, codigo, nombre, ruta, orden, implementada, activo)
        SELECT gen_random_uuid(), m.id, 'tipos_producto', 'Tipos de producto',
               '/dashboard/inventario/tipos-producto', 6, TRUE, TRUE
        FROM adm_modulo m WHERE m.codigo = 'inventario'
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO adm_permiso_opcion (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar)
        SELECT gen_random_uuid(), r.id, o.id, TRUE, TRUE, TRUE, TRUE
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'superadmin' AND o.codigo = 'tipos_producto'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table('inv_producto_um')
    op.drop_table('inv_producto')
    op.execute("DELETE FROM adm_permiso_opcion WHERE opcion_id IN (SELECT id FROM adm_opcion WHERE codigo = 'tipos_producto')")
    op.execute("DELETE FROM adm_opcion WHERE codigo = 'tipos_producto'")
    op.drop_table('inv_tipo_producto')
