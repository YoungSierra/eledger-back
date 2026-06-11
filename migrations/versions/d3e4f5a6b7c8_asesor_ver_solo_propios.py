"""asesor_id en tercero y cotizacion, ver_solo_propios en rol, es_asesor en usuario

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("adm_rol",
        sa.Column("ver_solo_propios", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("adm_usuario",
        sa.Column("es_asesor", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("adm_tercero",
        sa.Column("asesor_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("adm_usuario.id"), nullable=True))
    op.add_column("ope_cotizacion",
        sa.Column("asesor_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("adm_usuario.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("ope_cotizacion", "asesor_id")
    op.drop_column("adm_tercero", "asesor_id")
    op.drop_column("adm_usuario", "es_asesor")
    op.drop_column("adm_rol", "ver_solo_propios")
