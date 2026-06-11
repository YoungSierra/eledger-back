"""Mueve ver_solo_propios de adm_rol a adm_usuario

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("adm_rol", "ver_solo_propios")
    op.add_column("adm_usuario",
        sa.Column("ver_solo_propios", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("adm_usuario", "ver_solo_propios")
    op.add_column("adm_rol",
        sa.Column("ver_solo_propios", sa.Boolean(), nullable=False, server_default="false"))
