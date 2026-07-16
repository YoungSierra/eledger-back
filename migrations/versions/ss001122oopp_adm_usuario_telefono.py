"""adm_usuario telefono

Revision ID: ss001122oopp
Revises: rr990011nnoo
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa

revision = "ss001122oopp"
down_revision = "rr990011nnoo"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("adm_usuario", sa.Column("telefono", sa.String(30), nullable=True))


def downgrade():
    op.drop_column("adm_usuario", "telefono")
