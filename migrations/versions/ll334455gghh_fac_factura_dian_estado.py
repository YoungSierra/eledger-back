"""fac_factura: agregar dian_estado

Revision ID: ll334455gghh
Revises: kk223344ffgg
Create Date: 2026-06-10 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = 'll334455gghh'
down_revision: Union[str, None] = 'kk223344ffgg'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'fac_factura',
        sa.Column('dian_estado', sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        'chk_fac_dian_estado',
        'fac_factura',
        "dian_estado IN ('pendiente','enviada','aceptada','rechazada')",
    )


def downgrade() -> None:
    op.drop_constraint('chk_fac_dian_estado', 'fac_factura')
    op.drop_column('fac_factura', 'dian_estado')
