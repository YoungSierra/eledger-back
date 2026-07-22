"""Consolidación: operación agrupa 1..N cotizaciones (varios clientes)

- ope_cotizacion.operacion_id (FK→ope_operacion): invierte la relación a 1:N.
- ope_hawb.cotizacion_id (FK→ope_cotizacion): cada guía hija a su cliente.
- ope_evento.hawb_id (FK→ope_hawb): bitácora dirigida a un HAWB.
- Backfill desde la relación 1:1 actual y se elimina ope_operacion.cotizacion_id.

Revision ID: xx556677ttuu
Revises: ww445566sstt
Create Date: 2026-07-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "xx556677ttuu"
down_revision = "ww445566sstt"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Nuevas columnas (nullable)
    op.add_column("ope_cotizacion", sa.Column("operacion_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_cotizacion_operacion", "ope_cotizacion", "ope_operacion", ["operacion_id"], ["id"])
    op.create_index("idx_cotizacion_operacion", "ope_cotizacion", ["operacion_id"])

    op.add_column("ope_hawb", sa.Column("cotizacion_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_hawb_cotizacion", "ope_hawb", "ope_cotizacion", ["cotizacion_id"], ["id"])
    op.create_index("idx_hawb_cotizacion", "ope_hawb", ["cotizacion_id"])

    op.add_column("ope_evento", sa.Column("hawb_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_evento_hawb", "ope_evento", "ope_hawb", ["hawb_id"], ["id"])
    op.create_index("idx_evento_hawb", "ope_evento", ["hawb_id"])

    # 2) Backfill desde la relación 1:1 vigente
    op.execute("""
        UPDATE ope_cotizacion c
        SET operacion_id = o.id
        FROM ope_operacion o
        WHERE o.cotizacion_id = c.id
    """)
    op.execute("""
        UPDATE ope_hawb h
        SET cotizacion_id = o.cotizacion_id
        FROM ope_operacion o
        WHERE h.operacion_id = o.id
    """)

    # 3) Eliminar la FK 1:1 (con su unique/índice dependientes)
    op.drop_index("idx_operacion_cotizacion", table_name="ope_operacion")
    op.drop_column("ope_operacion", "cotizacion_id")


def downgrade():
    op.add_column("ope_operacion", sa.Column("cotizacion_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE ope_operacion o
        SET cotizacion_id = c.id
        FROM ope_cotizacion c
        WHERE c.operacion_id = o.id
    """)
    op.create_index("idx_operacion_cotizacion", "ope_operacion", ["cotizacion_id"])

    op.drop_index("idx_evento_hawb", table_name="ope_evento")
    op.drop_constraint("fk_evento_hawb", "ope_evento", type_="foreignkey")
    op.drop_column("ope_evento", "hawb_id")

    op.drop_index("idx_hawb_cotizacion", table_name="ope_hawb")
    op.drop_constraint("fk_hawb_cotizacion", "ope_hawb", type_="foreignkey")
    op.drop_column("ope_hawb", "cotizacion_id")

    op.drop_index("idx_cotizacion_operacion", table_name="ope_cotizacion")
    op.drop_constraint("fk_cotizacion_operacion", "ope_cotizacion", type_="foreignkey")
    op.drop_column("ope_cotizacion", "operacion_id")
