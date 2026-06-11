"""cnt_parametro_contable

Revision ID: ee55ff667788
Revises: dd44ee55ff66
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'ee55ff667788'
down_revision: Union[str, None] = 'dd44ee55ff66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIPOS = [
    'ENTRADA_COMPRA',
    'SALIDA_VENTA',
    'TRASLADO_SALIDA',
    'TRASLADO_ENTRADA',
    'AJUSTE_ENTRADA',
    'AJUSTE_SALIDA',
    'DEVOLUCION_CLIENTE',
    'DEVOLUCION_PROVEEDOR',
    'ENTRADA_PRODUCCION',
    'SALIDA_PRODUCCION',
]


def upgrade() -> None:
    op.create_table(
        'cnt_parametro_contable',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tipo_movimiento', sa.String(length=30), nullable=False),
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
        sa.UniqueConstraint('tipo_movimiento'),
    )

    # Sembrar las 10 filas fijas
    for tipo in TIPOS:
        op.execute(
            f"INSERT INTO cnt_parametro_contable (id, tipo_movimiento) "
            f"VALUES (gen_random_uuid(), '{tipo}')"
        )

    # Opción de menú bajo contabilidad
    op.execute("""
        INSERT INTO adm_opcion (id, modulo_id, codigo, nombre, ruta, orden, implementada, activo)
        SELECT gen_random_uuid(), m.id, 'parametros_contables', 'Parametrización contable',
               '/dashboard/contabilidad/parametros-contables', 5, TRUE, TRUE
        FROM adm_modulo m WHERE m.codigo = 'contabilidad'
        ON CONFLICT DO NOTHING
    """)

    # Permiso superadmin
    op.execute("""
        INSERT INTO adm_permiso_opcion (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar)
        SELECT gen_random_uuid(), r.id, o.id, TRUE, TRUE, TRUE, TRUE
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'superadmin' AND o.codigo = 'parametros_contables'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM adm_permiso_opcion WHERE opcion_id IN (SELECT id FROM adm_opcion WHERE codigo = 'parametros_contables')")
    op.execute("DELETE FROM adm_opcion WHERE codigo = 'parametros_contables'")
    op.drop_table('cnt_parametro_contable')
