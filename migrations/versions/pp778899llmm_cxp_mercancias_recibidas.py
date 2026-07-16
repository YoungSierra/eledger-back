"""cxp_parametro_contable: cuenta_mercancias_recibidas_id

Revision ID: pp778899llmm
Revises: oo667788kkll
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "pp778899llmm"
down_revision = "oo667788kkll"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cxp_parametro_contable",
        sa.Column("cuenta_mercancias_recibidas_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_cuenta.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("cxp_parametro_contable", "cuenta_mercancias_recibidas_id")
