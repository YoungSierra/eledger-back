"""drop_aeropuertos_cot_op

Elimina aeropuerto_origen_id y aeropuerto_destino_id de ope_cotizacion y ope_operacion.
Los aeropuertos son propios del MAWB/HAWB, no del encabezado comercial ni del contenedor.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-05 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ope_cotizacion
    op.drop_constraint("ope_cotizacion_aeropuerto_origen_id_fkey",  "ope_cotizacion", type_="foreignkey")
    op.drop_constraint("ope_cotizacion_aeropuerto_destino_id_fkey", "ope_cotizacion", type_="foreignkey")
    op.drop_column("ope_cotizacion", "aeropuerto_origen_id")
    op.drop_column("ope_cotizacion", "aeropuerto_destino_id")

    # ope_operacion
    op.drop_constraint("ope_operacion_aeropuerto_origen_id_fkey",  "ope_operacion", type_="foreignkey")
    op.drop_constraint("ope_operacion_aeropuerto_destino_id_fkey", "ope_operacion", type_="foreignkey")
    op.drop_column("ope_operacion", "aeropuerto_origen_id")
    op.drop_column("ope_operacion", "aeropuerto_destino_id")


def downgrade() -> None:
    # ope_operacion
    op.add_column("ope_operacion", sa.Column("aeropuerto_origen_id",  pg.UUID(as_uuid=True), nullable=True))
    op.add_column("ope_operacion", sa.Column("aeropuerto_destino_id", pg.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("ope_operacion_aeropuerto_origen_id_fkey",  "ope_operacion", "ope_aeropuerto", ["aeropuerto_origen_id"],  ["id"])
    op.create_foreign_key("ope_operacion_aeropuerto_destino_id_fkey", "ope_operacion", "ope_aeropuerto", ["aeropuerto_destino_id"], ["id"])

    # ope_cotizacion
    op.add_column("ope_cotizacion", sa.Column("aeropuerto_origen_id",  pg.UUID(as_uuid=True), nullable=True))
    op.add_column("ope_cotizacion", sa.Column("aeropuerto_destino_id", pg.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("ope_cotizacion_aeropuerto_origen_id_fkey",  "ope_cotizacion", "ope_aeropuerto", ["aeropuerto_origen_id"],  ["id"])
    op.create_foreign_key("ope_cotizacion_aeropuerto_destino_id_fkey", "ope_cotizacion", "ope_aeropuerto", ["aeropuerto_destino_id"], ["id"])
