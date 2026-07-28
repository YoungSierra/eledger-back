"""CxC — factura afectada por nota crédito/débito (referencia DIAN + cruce)

Revision ID: bc778899cxc2
Revises: bb667788cxc1
Create Date: 2026-07-24
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "bc778899cxc2"
down_revision = "bb667788cxc1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cxc_documento",
        sa.Column("factura_afectada_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cxc_doc_factura_afectada",
        "cxc_documento", "cxc_documento",
        ["factura_afectada_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_cxc_doc_factura_afectada", "cxc_documento", type_="foreignkey")
    op.drop_column("cxc_documento", "factura_afectada_id")
