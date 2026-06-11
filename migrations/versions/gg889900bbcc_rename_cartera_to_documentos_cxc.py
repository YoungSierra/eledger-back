"""rename_cartera_to_documentos_cxc

Renombra la opción de menú 'Cartera' a 'Documentos CxC' y actualiza su ruta.

Revision ID: gg889900bbcc
Revises: e6f7a8b9c0d1e2
Create Date: 2026-06-10 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'gg889900bbcc'
down_revision: Union[str, None] = 'e6f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE adm_opcion
        SET codigo = 'documentos_cxc', nombre = 'Documentos CxC', ruta = '/dashboard/cxc/documentos'
        WHERE codigo = 'cartera'
          AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'cxc')
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE adm_opcion
        SET codigo = 'cartera', nombre = 'Cartera', ruta = '/dashboard/cxc/cartera'
        WHERE codigo = 'documentos_cxc'
          AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'cxc')
    """)
