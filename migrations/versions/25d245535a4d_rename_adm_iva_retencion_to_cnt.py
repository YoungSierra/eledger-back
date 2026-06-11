"""rename_adm_iva_retencion_to_cnt

Revision ID: 25d245535a4d
Revises: 23f95a53939d
Create Date: 2026-06-06 17:40:40.848489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '25d245535a4d'
down_revision: Union[str, None] = '23f95a53939d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("adm_tarifa_iva", "cnt_tarifa_iva")
    op.rename_table("adm_retencion",  "cnt_retencion")


def downgrade() -> None:
    op.rename_table("cnt_tarifa_iva", "adm_tarifa_iva")
    op.rename_table("cnt_retencion",  "adm_retencion")
