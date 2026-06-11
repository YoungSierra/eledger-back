"""inv_bodega

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'inv_bodega',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('direccion', sa.Text(), nullable=True),
        sa.Column('responsable_id', sa.UUID(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', sa.UUID(), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['responsable_id'], ['adm_usuario.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo'),
    )

    op.execute("UPDATE adm_opcion SET implementada = TRUE WHERE codigo = 'bodegas'")


def downgrade() -> None:
    op.execute("UPDATE adm_opcion SET implementada = FALSE WHERE codigo = 'bodegas'")
    op.drop_table('inv_bodega')
