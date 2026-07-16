"""oc_linea: tarifa_iva_id y centro_costo_id

Revision ID: oo667788kkll
Revises: nn556677iijj
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "oo667788kkll"
down_revision = "nn556677iijj"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("com_oc_linea",
        sa.Column("tarifa_iva_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_tarifa_iva.id"), nullable=True))
    op.add_column("com_oc_linea",
        sa.Column("centro_costo_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_centro_costo.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("com_oc_linea", "centro_costo_id")
    op.drop_column("com_oc_linea", "tarifa_iva_id")
