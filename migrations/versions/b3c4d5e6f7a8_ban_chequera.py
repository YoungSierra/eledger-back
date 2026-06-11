"""ban_chequera

Crea la tabla ban_chequera para talonarios de cheques asociados a cuentas bancarias.

Revision ID: b3c4d5e6f7a8
Revises: 3a11a32829f8
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = '3a11a32829f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ban_chequera',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('cuenta_id', sa.UUID(as_uuid=True), sa.ForeignKey('ban_cuenta.id'), nullable=False),
        sa.Column('prefijo', sa.String(10), nullable=True),
        sa.Column('numero_desde', sa.Integer(), nullable=False),
        sa.Column('numero_hasta', sa.Integer(), nullable=False),
        sa.Column('consecutivo_actual', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(10), nullable=False, server_default='ACTIVA'),
        sa.Column('descripcion', sa.String(255), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('creado_por', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('eliminado', sa.Boolean(), nullable=False, server_default='false'),
        sa.CheckConstraint("estado IN ('ACTIVA','AGOTADA','ANULADA')", name='chk_ban_chequera_estado'),
    )


def downgrade() -> None:
    op.drop_table('ban_chequera')
