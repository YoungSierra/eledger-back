"""cnt_asiento y cnt_asiento_linea

Revision ID: a1b2c3d4e5f7
Revises: ff778899aabb
Create Date: 2026-06-08 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, tuple] = ("ff778899aabb", "cc33dd44ee55")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Secuencia para el número incremental interno del libro mayor
    op.execute("CREATE SEQUENCE cnt_asiento_numero_seq START 1 INCREMENT 1")

    op.create_table(
        "cnt_asiento",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.BigInteger(), nullable=False,
                  server_default=sa.text("nextval('cnt_asiento_numero_seq')")),
        sa.Column("documento_numero", sa.String(30), nullable=True),
        sa.Column("tipo_documento_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("adm_tipo_documento.id"), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("periodo_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_periodo.id"), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("documento_origen_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("documento_origen_tipo", sa.String(50), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="borrador"),
        sa.Column("moneda_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("adm_moneda.id"), nullable=False),
        sa.Column("trm", sa.Numeric(18, 6), nullable=True),
        sa.Column("asiento_origen_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        # auditoría
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("creado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("numero", name="uq_asiento_numero"),
        sa.UniqueConstraint("documento_numero", name="uq_asiento_documento_numero"),
        sa.CheckConstraint("estado IN ('borrador','publicado')", name="chk_asiento_estado"),
        sa.ForeignKeyConstraint(["asiento_origen_id"], ["cnt_asiento.id"],
                                name="fk_asiento_origen"),
    )
    op.create_index("idx_asiento_fecha", "cnt_asiento", ["fecha"])
    op.create_index("idx_asiento_periodo", "cnt_asiento", ["periodo_id"])
    op.create_index("idx_asiento_estado", "cnt_asiento", ["estado"])
    op.create_index("idx_asiento_tipo_doc", "cnt_asiento", ["tipo_documento_id"])

    op.create_table(
        "cnt_asiento_linea",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asiento_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_asiento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orden", sa.SmallInteger(), nullable=False),
        sa.Column("cuenta_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_cuenta.id"), nullable=False),
        sa.Column("debito", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("credito", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("debito_funcional", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("credito_funcional", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("tercero_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("adm_tercero.id"), nullable=True),
        sa.Column("centro_costo_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cnt_centro_costo.id"), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.CheckConstraint(
            "(debito > 0 AND credito = 0) OR (credito > 0 AND debito = 0)",
            name="chk_linea_debito_credito"
        ),
    )
    op.create_index("idx_asiento_linea_asiento", "cnt_asiento_linea", ["asiento_id"])
    op.create_index("idx_asiento_linea_cuenta", "cnt_asiento_linea", ["cuenta_id"])
    op.create_index("idx_asiento_linea_tercero", "cnt_asiento_linea", ["tercero_id"])


def downgrade() -> None:
    op.drop_table("cnt_asiento_linea")
    op.drop_table("cnt_asiento")
    op.execute("DROP SEQUENCE cnt_asiento_numero_seq")
