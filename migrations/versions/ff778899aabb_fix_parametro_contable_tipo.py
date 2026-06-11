"""fix_parametro_contable_tipo

Corrige cnt_parametro_contable: reemplaza las 10 filas de tipo movimiento
por las 4 filas correctas de tipo producto según el diseño fase-3.

Revision ID: ff778899aabb
Revises: ee55ff667788
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'ff778899aabb'
down_revision: Union[str, None] = 'ee55ff667788'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM cnt_parametro_contable")
    for tipo in ('MERCANCIA', 'SERVICIO', 'MATERIA_PRIMA', 'INSUMO'):
        op.execute(
            f"INSERT INTO cnt_parametro_contable (id, tipo_movimiento) "
            f"VALUES (gen_random_uuid(), '{tipo}')"
        )


def downgrade() -> None:
    op.execute("DELETE FROM cnt_parametro_contable")
    for tipo in (
        'ENTRADA_COMPRA', 'SALIDA_VENTA', 'TRASLADO_SALIDA', 'TRASLADO_ENTRADA',
        'AJUSTE_ENTRADA', 'AJUSTE_SALIDA', 'DEVOLUCION_CLIENTE', 'DEVOLUCION_PROVEEDOR',
        'ENTRADA_PRODUCCION', 'SALIDA_PRODUCCION',
    ):
        op.execute(
            f"INSERT INTO cnt_parametro_contable (id, tipo_movimiento) "
            f"VALUES (gen_random_uuid(), '{tipo}')"
        )
