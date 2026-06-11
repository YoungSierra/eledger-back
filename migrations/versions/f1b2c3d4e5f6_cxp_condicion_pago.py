"""cxp_documento: agregar condicion_pago_id

Revision ID: f1b2c3d4e5f6
Revises: e0f1a2b3c4d5
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f1b2c3d4e5f6'
down_revision = 'e0f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cxp_documento',
        sa.Column('condicion_pago_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_cxp_condicion_pago', 'cxp_documento',
        'adm_condicion_pago', ['condicion_pago_id'], ['id']
    )


def downgrade():
    op.drop_constraint('fk_cxp_condicion_pago', 'cxp_documento', type_='foreignkey')
    op.drop_column('cxp_documento', 'condicion_pago_id')
