"""Documentos de transporte marítimo — MBL, HBL y contenedores

El módulo ope_ modelaba solo aéreo. Estas tablas calcan la jerarquía MAWB→HAWB
pero con los datos del marítimo, que no caben en las aéreas: contenedor, sello,
CBM, tara, puertos, booking.

Conviven con las aéreas a propósito: una operación es multimodal. En los datos
actuales 28 de 32 cotizaciones ya cobran un tramo terrestre además del
internacional.

Naviera y puertos NO llevan catálogo nuevo: ope_aerolinea y ope_aeropuerto ya
nacieron con campo `modalidad`, y se usan filtrando por MARITIMA.

Decisiones del esquema
- ope_hbl_contenedor es N:M porque un HBL puede amparar varios contenedores y un
  contenedor puede llevar varios HBL (LCL). Lleva piezas/peso/CBM propios: en
  LCL cada casa aporta su parte del mismo contenedor.
- ope_bl_cargo es tabla y no un flag prepaid/collect porque al emitir el HBL en
  exportación el flete se imprime desglosado.
- El HBL tiene ciclo de vida (BORRADOR/EMITIDA/ANULADA) y `origen`: en
  importación se RECIBE del agente, en exportación lo EMITE Universal Cargo.
- ETD, ETA y fecha_arribo no vienen en el BL, pero sin ellas no se puede hacer
  el seguimiento que hoy hacen dos o tres veces por semana.
- free_days y referencia_cliente hoy se anotan a mano en las notas de la
  cotización; ver COT-20260030.

Revision ID: rr33oopp0001
Revises: qq22nnoo0001
"""
from alembic import op
import sqlalchemy as sa

revision = "rr33oopp0001"
down_revision = "qq22nnoo0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ope_mbl",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operacion_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_operacion.id"), nullable=False),
        sa.Column("naviera_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_aerolinea.id"), nullable=True),
        sa.Column("numero_bl", sa.String(50), nullable=False),
        sa.Column("booking_no", sa.String(50), nullable=True),
        sa.Column("export_references", sa.String(120), nullable=True),
        sa.Column("referencia_cliente", sa.String(120), nullable=True),
        sa.Column("shipper_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=True),
        sa.Column("shipper_texto", sa.Text(), nullable=True),
        sa.Column("consignee_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=True),
        sa.Column("consignee_texto", sa.Text(), nullable=True),
        sa.Column("notify_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=True),
        sa.Column("notify_texto", sa.Text(), nullable=True),
        sa.Column("agente_destino", sa.Text(), nullable=True),
        sa.Column("pre_carriage_by", sa.String(120), nullable=True),
        sa.Column("place_of_receipt", sa.String(120), nullable=True),
        sa.Column("puerto_embarque_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_aeropuerto.id"), nullable=True),
        sa.Column("puerto_descarga_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_aeropuerto.id"), nullable=True),
        sa.Column("place_of_delivery", sa.String(120), nullable=True),
        sa.Column("onward_inland_routing", sa.Text(), nullable=True),
        sa.Column("buque", sa.String(120), nullable=True),
        sa.Column("viaje", sa.String(40), nullable=True),
        sa.Column("fecha_emision", sa.Date(), nullable=True),
        sa.Column("lugar_emision", sa.String(120), nullable=True),
        sa.Column("shipped_on_board", sa.Date(), nullable=True),
        sa.Column("etd", sa.Date(), nullable=True),
        sa.Column("eta", sa.Date(), nullable=True),
        sa.Column("fecha_arribo", sa.Date(), nullable=True),
        sa.Column("termino", sa.String(20), nullable=True),
        sa.Column("tipo_carga", sa.String(5), nullable=False, server_default=sa.text("'FCL'")),
        sa.Column("tipo_pago_flete", sa.String(10), nullable=False, server_default=sa.text("'PREPAID'")),
        sa.Column("freight_to_be_paid_at", sa.String(120), nullable=True),
        sa.Column("num_originales", sa.SmallInteger(), nullable=True),
        sa.Column("declared_value", sa.String(80), nullable=True),
        sa.Column("free_days", sa.SmallInteger(), nullable=True),
        sa.Column("say_total", sa.Text(), nullable=True),
        sa.Column("marcas", sa.Text(), nullable=True),
        sa.Column("descripcion_mercancia", sa.Text(), nullable=True),
        sa.Column("bultos_cantidad", sa.Integer(), nullable=True),
        sa.Column("bultos_clase", sa.String(60), nullable=True),
        sa.Column("carrier_receipt", sa.String(120), nullable=True),
        sa.Column("peso_bruto_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("tara_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("cbm", sa.Numeric(18, 4), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("creado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("tipo_carga IN ('FCL','LCL')", name="chk_mbl_tipo_carga"),
        sa.CheckConstraint("tipo_pago_flete IN ('PREPAID','COLLECT')", name="chk_mbl_pago_flete"),
    )
    op.create_index("idx_mbl_numero", "ope_mbl", ["numero_bl"])
    op.create_index("idx_mbl_booking", "ope_mbl", ["booking_no"])
    op.create_index("idx_mbl_operacion", "ope_mbl", ["operacion_id"])

    op.create_table(
        "ope_hbl",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operacion_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_operacion.id"), nullable=False),
        sa.Column("mbl_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_mbl.id"), nullable=True),
        sa.Column("cotizacion_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_cotizacion.id"), nullable=True),
        sa.Column("origen", sa.String(10), nullable=False, server_default=sa.text("'RECIBIDO'")),
        sa.Column("emisor_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=True),
        sa.Column("emisor_texto", sa.Text(), nullable=True),
        sa.Column("numero_hbl", sa.String(50), nullable=False),
        sa.Column("booking_no", sa.String(50), nullable=True),
        sa.Column("export_references", sa.String(120), nullable=True),
        sa.Column("referencia_cliente", sa.String(120), nullable=True),
        sa.Column("do_numero", sa.String(50), nullable=True),
        sa.Column("shipper_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=True),
        sa.Column("shipper_texto", sa.Text(), nullable=True),
        sa.Column("consignee_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=True),
        sa.Column("consignee_texto", sa.Text(), nullable=True),
        sa.Column("consignee_a_la_orden", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notify_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("adm_tercero.id"), nullable=True),
        sa.Column("notify_texto", sa.Text(), nullable=True),
        sa.Column("agente_entrega", sa.Text(), nullable=True),
        sa.Column("pre_carriage_by", sa.String(120), nullable=True),
        sa.Column("place_of_receipt", sa.String(120), nullable=True),
        sa.Column("puerto_embarque_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_aeropuerto.id"), nullable=True),
        sa.Column("puerto_descarga_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_aeropuerto.id"), nullable=True),
        sa.Column("place_of_delivery", sa.String(120), nullable=True),
        sa.Column("onward_inland_routing", sa.Text(), nullable=True),
        sa.Column("buque", sa.String(120), nullable=True),
        sa.Column("viaje", sa.String(40), nullable=True),
        sa.Column("fecha_emision", sa.Date(), nullable=True),
        sa.Column("lugar_emision", sa.String(120), nullable=True),
        sa.Column("shipped_on_board", sa.Date(), nullable=True),
        sa.Column("etd", sa.Date(), nullable=True),
        sa.Column("eta", sa.Date(), nullable=True),
        sa.Column("fecha_arribo", sa.Date(), nullable=True),
        sa.Column("termino", sa.String(20), nullable=True),
        sa.Column("tipo_carga", sa.String(5), nullable=False, server_default=sa.text("'FCL'")),
        sa.Column("tipo_pago_flete", sa.String(10), nullable=False, server_default=sa.text("'PREPAID'")),
        sa.Column("freight_to_be_paid_at", sa.String(120), nullable=True),
        sa.Column("num_originales", sa.SmallInteger(), nullable=True),
        sa.Column("declared_value", sa.String(80), nullable=True),
        sa.Column("say_total", sa.Text(), nullable=True),
        sa.Column("marcas", sa.Text(), nullable=True),
        sa.Column("descripcion_mercancia", sa.Text(), nullable=True),
        sa.Column("bultos_cantidad", sa.Integer(), nullable=True),
        sa.Column("bultos_clase", sa.String(60), nullable=True),
        sa.Column("carrier_receipt", sa.String(120), nullable=True),
        sa.Column("peso_bruto_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("cbm", sa.Numeric(18, 4), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default=sa.text("'BORRADOR'")),
        sa.Column("emitido_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("emitido_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_motivo", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("creado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("origen IN ('RECIBIDO','EMITIDO')", name="chk_hbl_origen"),
        sa.CheckConstraint("tipo_carga IN ('FCL','LCL')", name="chk_hbl_tipo_carga"),
        sa.CheckConstraint("estado IN ('BORRADOR','EMITIDA','ANULADA')", name="chk_hbl_estado"),
        sa.CheckConstraint("tipo_pago_flete IN ('PREPAID','COLLECT')", name="chk_hbl_pago_flete"),
    )
    op.create_index("idx_hbl_booking", "ope_hbl", ["booking_no"])
    op.create_index("idx_hbl_operacion", "ope_hbl", ["operacion_id"])
    op.create_index("idx_hbl_mbl", "ope_hbl", ["mbl_id"])
    op.create_index("idx_hbl_numero", "ope_hbl", ["numero_hbl"])
    op.create_index("ix_ope_hbl_cotizacion_id", "ope_hbl", ["cotizacion_id"])

    op.create_table(
        "ope_contenedor",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operacion_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_operacion.id"), nullable=False),
        sa.Column("mbl_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_mbl.id"), nullable=True),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("sello", sa.String(40), nullable=True),
        sa.Column("tipo", sa.String(15), nullable=True),
        sa.Column("tara_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("peso_bruto_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("cbm", sa.Numeric(18, 4), nullable=True),
        sa.Column("fecha_devolucion", sa.Date(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("creado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("idx_contenedor_operacion", "ope_contenedor", ["operacion_id"])
    op.create_index("idx_contenedor_numero", "ope_contenedor", ["numero"])

    op.create_table(
        "ope_hbl_contenedor",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hbl_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_hbl.id"), nullable=False),
        sa.Column("contenedor_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_contenedor.id"), nullable=False),
        sa.Column("piezas", sa.Integer(), nullable=True),
        sa.Column("peso_kg", sa.Numeric(18, 4), nullable=True),
        sa.Column("cbm", sa.Numeric(18, 4), nullable=True),
        sa.UniqueConstraint("hbl_id", "contenedor_id", name="uq_hbl_contenedor"),
    )
    op.create_index("idx_hbl_cont_contenedor", "ope_hbl_contenedor", ["contenedor_id"])
    op.create_index("idx_hbl_cont_hbl", "ope_hbl_contenedor", ["hbl_id"])

    op.create_table(
        "ope_bl_cargo",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hbl_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ope_hbl.id"), nullable=False),
        sa.Column("orden", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("concepto", sa.String(120), nullable=False),
        sa.Column("tarifa", sa.Numeric(18, 4), nullable=True),
        sa.Column("unidad", sa.String(30), nullable=True),
        sa.Column("moneda", sa.String(3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("valor", sa.Numeric(18, 4), nullable=True),
        sa.Column("pago", sa.String(10), nullable=False, server_default=sa.text("'PREPAID'")),
        sa.CheckConstraint("pago IN ('PREPAID','COLLECT')", name="chk_bl_cargo_pago"),
    )
    op.create_index("idx_bl_cargo_hbl", "ope_bl_cargo", ["hbl_id"])


def downgrade() -> None:
    op.drop_table("ope_bl_cargo")
    op.drop_table("ope_hbl_contenedor")
    op.drop_table("ope_contenedor")
    op.drop_table("ope_hbl")
    op.drop_table("ope_mbl")

