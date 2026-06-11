"""cxp_linea_retencion: cuenta_id nullable

Revision ID: a2b3c4d5e6f7
Revises: f1b2c3d4e5f6
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7a8b9'
down_revision = 'f1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('cxp_linea_retencion', 'cuenta_id', nullable=True)


def downgrade():
    op.alter_column('cxp_linea_retencion', 'cuenta_id', nullable=False)
