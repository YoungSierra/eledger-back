"""cxp_aplicacion: agregar campo estado

Revision ID: e6f7a8b9c0d1e2
Revises: d5e6f7a8b9c0d1
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e6f7a8b9c0d1e2'
down_revision = 'd5e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cxp_aplicacion',
        sa.Column('estado', sa.String(10), nullable=False, server_default='aplicado')
    )
    op.create_check_constraint(
        'chk_cxp_app_estado', 'cxp_aplicacion',
        "estado IN ('pendiente','aplicado')"
    )


def downgrade():
    op.drop_constraint('chk_cxp_app_estado', 'cxp_aplicacion', type_='check')
    op.drop_column('cxp_aplicacion', 'estado')
