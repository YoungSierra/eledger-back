"""resoluciones_implementada

Marca la opción Resoluciones DIAN como implementada.

Revision ID: hh990011ccdd
Revises: gg889900bbcc
Create Date: 2026-06-10 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'hh990011ccdd'
down_revision: Union[str, None] = 'gg889900bbcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE adm_opcion SET implementada = true
        WHERE codigo = 'resoluciones'
          AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'facturacion')
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE adm_opcion SET implementada = false
        WHERE codigo = 'resoluciones'
          AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'facturacion')
    """)
