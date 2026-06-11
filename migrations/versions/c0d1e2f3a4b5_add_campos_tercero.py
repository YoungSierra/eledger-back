"""add pais contacto notas to adm_tercero

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("adm_tercero", sa.Column("pais", sa.String(100), nullable=True))
    op.add_column("adm_tercero", sa.Column("codigo_postal", sa.String(20), nullable=True))
    op.add_column("adm_tercero", sa.Column("nombre_contacto", sa.String(150), nullable=True))
    op.add_column("adm_tercero", sa.Column("cargo_contacto", sa.String(100), nullable=True))
    op.add_column("adm_tercero", sa.Column("telefono_contacto", sa.String(20), nullable=True))
    op.add_column("adm_tercero", sa.Column("email_contacto", sa.String(100), nullable=True))
    op.add_column("adm_tercero", sa.Column("notas", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("adm_tercero", "notas")
    op.drop_column("adm_tercero", "email_contacto")
    op.drop_column("adm_tercero", "telefono_contacto")
    op.drop_column("adm_tercero", "cargo_contacto")
    op.drop_column("adm_tercero", "nombre_contacto")
    op.drop_column("adm_tercero", "codigo_postal")
    op.drop_column("adm_tercero", "pais")
