"""cxc_documento, cxc_retencion, cxc_aplicacion

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f7
Create Date: 2026-06-08 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = sa.dialects.postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "cxc_documento",
        sa.Column("id",               UUID,         primary_key=True),
        sa.Column("numero",           sa.String(30), nullable=False),
        sa.Column("tipo",             sa.String(20), nullable=False),
        sa.Column("fecha",            sa.Date(),     nullable=False),
        sa.Column("fecha_vencimiento",sa.Date(),     nullable=True),
        sa.Column("periodo_id",       UUID, sa.ForeignKey("cnt_periodo.id"),  nullable=False),
        sa.Column("tercero_id",       UUID, sa.ForeignKey("adm_tercero.id"),  nullable=False),
        sa.Column("moneda_id",        UUID, sa.ForeignKey("adm_moneda.id"),   nullable=False),
        sa.Column("trm",              sa.Numeric(18,6), nullable=True),
        sa.Column("subtotal",         sa.Numeric(18,4), nullable=False, server_default="0"),
        sa.Column("total_iva",        sa.Numeric(18,4), nullable=False, server_default="0"),
        sa.Column("total_retenciones",sa.Numeric(18,4), nullable=False, server_default="0"),
        sa.Column("total",            sa.Numeric(18,4), nullable=False, server_default="0"),
        sa.Column("saldo",            sa.Numeric(18,4), nullable=False, server_default="0"),
        sa.Column("descripcion",      sa.Text(),     nullable=True),
        sa.Column("estado",           sa.String(20), nullable=False, server_default="borrador"),
        sa.Column("asiento_id",       UUID, sa.ForeignKey("cnt_asiento.id"), nullable=True),
        sa.Column("asiento_modificado_manual", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("origen_modulo",    sa.String(50), nullable=True),
        sa.Column("origen_id",        UUID,          nullable=True),
        sa.Column("documento_origen_id", UUID, nullable=True),
        # auditoría
        sa.Column("activo",        sa.Boolean(),            nullable=False, server_default="true"),
        sa.Column("creado_en",     sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("creado_por",    UUID, nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por",UUID, nullable=True),
        sa.UniqueConstraint("numero", name="uq_cxc_numero"),
        sa.CheckConstraint("tipo IN ('FACTURA','RECIBO','NOTA_CREDITO','NOTA_DEBITO','ANTICIPO')", name="chk_cxc_tipo"),
        sa.CheckConstraint("estado IN ('borrador','contabilizado','anulado')", name="chk_cxc_estado"),
        sa.CheckConstraint("saldo >= 0", name="chk_cxc_saldo"),
        sa.CheckConstraint("total >= 0", name="chk_cxc_total"),
        sa.CheckConstraint(
            "tipo NOT IN ('FACTURA','NOTA_DEBITO') OR fecha_vencimiento IS NOT NULL",
            name="chk_cxc_vencimiento"
        ),
        sa.ForeignKeyConstraint(["documento_origen_id"], ["cxc_documento.id"], name="fk_cxc_origen"),
    )
    op.create_index("idx_cxc_tercero",     "cxc_documento", ["tercero_id"])
    op.create_index("idx_cxc_estado",      "cxc_documento", ["estado"])
    op.create_index("idx_cxc_fecha",       "cxc_documento", ["fecha"])
    op.create_index("idx_cxc_tipo",        "cxc_documento", ["tipo"])
    op.create_index("idx_cxc_vencimiento", "cxc_documento", ["fecha_vencimiento"])

    op.create_table(
        "cxc_retencion",
        sa.Column("id",           UUID, primary_key=True),
        sa.Column("documento_id", UUID, sa.ForeignKey("cxc_documento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo",         sa.String(20),  nullable=False),
        sa.Column("concepto",     sa.String(100), nullable=False),
        sa.Column("base",         sa.Numeric(18,4), nullable=False),
        sa.Column("porcentaje",   sa.Numeric(8,4),  nullable=False),
        sa.Column("valor",        sa.Numeric(18,4), nullable=False),
        sa.Column("cuenta_id",    UUID, sa.ForeignKey("cnt_cuenta.id"), nullable=False),
        sa.CheckConstraint("tipo IN ('RETEFUENTE','RETEICA','RETEIVA')", name="chk_cxc_ret_tipo"),
    )
    op.create_index("idx_cxc_ret_documento", "cxc_retencion", ["documento_id"])

    op.create_table(
        "cxc_aplicacion",
        sa.Column("id",                   UUID, primary_key=True),
        sa.Column("documento_credito_id", UUID, sa.ForeignKey("cxc_documento.id"), nullable=False),
        sa.Column("documento_debito_id",  UUID, sa.ForeignKey("cxc_documento.id"), nullable=False),
        sa.Column("valor",                sa.Numeric(18,4), nullable=False),
        sa.Column("fecha",                sa.Date(),        nullable=False),
        sa.Column("creado_en",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("creado_por", UUID, nullable=False),
        sa.CheckConstraint("valor > 0", name="chk_cxc_app_valor"),
        sa.CheckConstraint("documento_credito_id <> documento_debito_id", name="chk_cxc_app_distintos"),
    )
    op.create_index("idx_cxc_app_credito", "cxc_aplicacion", ["documento_credito_id"])
    op.create_index("idx_cxc_app_debito",  "cxc_aplicacion", ["documento_debito_id"])


def downgrade() -> None:
    op.drop_table("cxc_aplicacion")
    op.drop_table("cxc_retencion")
    op.drop_table("cxc_documento")
