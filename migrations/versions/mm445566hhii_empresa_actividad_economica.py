"""adm_empresa actividad_economica

Revision ID: mm445566hhii
Revises: ll334455gghh
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "mm445566hhii"
down_revision = "ll334455gghh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("adm_empresa", sa.Column("actividad_economica_codigo", sa.String(10), nullable=True))
    op.add_column("adm_empresa", sa.Column("actividad_economica_descripcion", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("adm_empresa", "actividad_economica_descripcion")
    op.drop_column("adm_empresa", "actividad_economica_codigo")
