"""fac_factura_linea: agregar centro_costo_id

Revision ID: kk223344ffgg
Revises: jj112233eeff
Create Date: 2026-06-10 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from alembic import op

revision: str = 'kk223344ffgg'
down_revision: Union[str, None] = 'jj112233eeff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'fac_factura_linea',
        sa.Column(
            'centro_costo_id',
            pg.UUID(as_uuid=True),
            sa.ForeignKey('cnt_centro_costo.id'),
            nullable=True,
        ),
    )
    op.create_index('idx_fac_linea_cc', 'fac_factura_linea', ['centro_costo_id'])


def downgrade() -> None:
    op.drop_index('idx_fac_linea_cc', 'fac_factura_linea')
    op.drop_column('fac_factura_linea', 'centro_costo_id')
