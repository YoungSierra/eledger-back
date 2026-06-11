"""drop_cnt_parametro_contable

Elimina la tabla cnt_parametro_contable — reemplazada por inv_tipo_producto
(migración aabb11223344). La tabla fue recreada por create_all al quedar
el modelo en código. El modelo fue eliminado en esta misma sesión.

Revision ID: ii001122ddee
Revises: hh990011ccdd
Create Date: 2026-06-10 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'ii001122ddee'
down_revision: Union[str, None] = 'hh990011ccdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('cnt_parametro_contable')


def downgrade() -> None:
    pass  # no se recrea — usar inv_tipo_producto
