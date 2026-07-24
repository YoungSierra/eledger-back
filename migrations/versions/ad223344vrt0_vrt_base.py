"""VRT (Valores Recibidos para Terceros) — base

Fase 0 del flujo de valores recibidos para terceros:
- cxc_parametro_contable.cuenta_valores_terceros_id  (cuenta 2815)
- ope_concepto.es_valor_tercero                      (default de la marca)
- ope_cotizacion_linea.valor_tercero                 (marca opcional en cotización)
- cxp_documento: se amplía el CHECK de 'tipo' para incluir 'VRT'
- Consecutivo del tipo de documento 'VRT' (módulo cxp)

El VRT vive en la misma tabla cxp_documento con tipo='VRT'; se enlaza a su
factura de venta origen por origen_modulo='facturacion' + origen_id (ya existen).

Revision ID: ad223344vrt0
Revises: ac112233xxyy
Create Date: 2026-07-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ad223344vrt0"
down_revision = "ac112233xxyy"
branch_labels = None
depends_on = None


def upgrade():
    # Parámetro CxC: cuenta de valores recibidos para terceros (2815).
    op.add_column(
        "cxc_parametro_contable",
        sa.Column("cuenta_valores_terceros_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cxc_param_cuenta_valores_terceros",
        "cxc_parametro_contable", "cnt_cuenta",
        ["cuenta_valores_terceros_id"], ["id"],
    )

    # Concepto operativo: default de la marca "valor recibido para tercero".
    op.add_column(
        "ope_concepto",
        sa.Column("es_valor_tercero", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Línea de cotización: marca opcional.
    op.add_column(
        "ope_cotizacion_linea",
        sa.Column("valor_tercero", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # cxp_documento: ampliar el CHECK de tipo para admitir 'VRT'.
    op.drop_constraint("chk_cxp_tipo", "cxp_documento", type_="check")
    op.create_check_constraint(
        "chk_cxp_tipo", "cxp_documento",
        "tipo IN ('FACTURA','COMPROBANTE','NOTA_CREDITO','NOTA_DEBITO','ANTICIPO','VRT')",
    )

    # Consecutivo del tipo de documento VRT.
    op.execute("""
        INSERT INTO adm_tipo_documento (id, codigo, nombre, modulo, activo)
        VALUES (gen_random_uuid(), 'VRT', 'Valor recibido para tercero', 'cxp', TRUE)
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO adm_consecutivo (id, tipo_documento_id, prefijo, numero_actual, numero_inicio, longitud_minima, activo)
        SELECT gen_random_uuid(), td.id, 'VRT-', 0, 1, 5, TRUE
        FROM adm_tipo_documento td
        WHERE td.codigo = 'VRT'
        ON CONFLICT DO NOTHING
    """)


def downgrade():
    op.execute("DELETE FROM adm_consecutivo WHERE tipo_documento_id = (SELECT id FROM adm_tipo_documento WHERE codigo='VRT')")
    op.execute("DELETE FROM adm_tipo_documento WHERE codigo = 'VRT'")

    op.drop_constraint("chk_cxp_tipo", "cxp_documento", type_="check")
    op.create_check_constraint(
        "chk_cxp_tipo", "cxp_documento",
        "tipo IN ('FACTURA','COMPROBANTE','NOTA_CREDITO','NOTA_DEBITO','ANTICIPO')",
    )

    op.drop_column("ope_cotizacion_linea", "valor_tercero")
    op.drop_column("ope_concepto", "es_valor_tercero")
    op.drop_constraint("fk_cxc_param_cuenta_valores_terceros", "cxc_parametro_contable", type_="foreignkey")
    op.drop_column("cxc_parametro_contable", "cuenta_valores_terceros_id")
