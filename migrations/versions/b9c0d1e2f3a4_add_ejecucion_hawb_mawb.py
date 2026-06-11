"""add fecha_ejecucion lugar_ejecucion to hawb and mawb

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ope_hawb", sa.Column("fecha_ejecucion", sa.Date(), nullable=True))
    op.add_column("ope_hawb", sa.Column("lugar_ejecucion", sa.String(100), nullable=True))
    op.add_column("ope_mawb", sa.Column("fecha_ejecucion", sa.Date(), nullable=True))
    op.add_column("ope_mawb", sa.Column("lugar_ejecucion", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("ope_hawb", "lugar_ejecucion")
    op.drop_column("ope_hawb", "fecha_ejecucion")
    op.drop_column("ope_mawb", "lugar_ejecucion")
    op.drop_column("ope_mawb", "fecha_ejecucion")
