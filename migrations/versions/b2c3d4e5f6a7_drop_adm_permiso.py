"""drop_adm_permiso

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-03 00:00:00.000000

adm_permiso (permisos a nivel de módulo) nunca se usa en las verificaciones
de acceso — el sistema usa adm_permiso_opcion (nivel de opción de menú).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('adm_permiso')


def downgrade() -> None:
    op.create_table(
        'adm_permiso',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rol_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modulo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('puede_ver', sa.Boolean(), nullable=False),
        sa.Column('puede_crear', sa.Boolean(), nullable=False),
        sa.Column('puede_editar', sa.Boolean(), nullable=False),
        sa.Column('puede_eliminar', sa.Boolean(), nullable=False),
        sa.Column('puede_imprimir', sa.Boolean(), nullable=False),
        sa.Column('puede_autorizar', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['modulo_id'], ['adm_modulo.id']),
        sa.ForeignKeyConstraint(['rol_id'], ['adm_rol.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rol_id', 'modulo_id', name='uq_permiso_rol_modulo'),
    )
