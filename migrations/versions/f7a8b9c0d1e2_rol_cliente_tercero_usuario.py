"""rol_cliente_tercero_usuario

Agrega es_cliente a adm_rol y tercero_id a adm_usuario para el portal de cliente.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-05 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('adm_rol', sa.Column('es_cliente', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('adm_usuario', sa.Column('tercero_id', sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_usuario_tercero', 'adm_usuario', 'adm_tercero', ['tercero_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_usuario_tercero', 'adm_usuario', type_='foreignkey')
    op.drop_column('adm_usuario', 'tercero_id')
    op.drop_column('adm_rol', 'es_cliente')
