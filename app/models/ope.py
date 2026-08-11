from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


# Orden de presentación de las secciones: sigue el recorrido físico del embarque,
# no el alfabético. Ordenar por el string deja GASTOS_DESTINO antes que
# GASTOS_ORIGEN, que es justo al revés de como se cotiza.
SECCIONES_ORDEN = [
    "TRANSPORTE_INTERNACIONAL",
    "GASTOS_ORIGEN",
    "GASTOS_DESTINO",
    "ADUANA",
    "TRANSPORTE_TERRESTRE",
    "ALMACENAMIENTO",
    "SEGURO",
]
_SECCIONES = "(" + ",".join(f"'{s}'" for s in SECCIONES_ORDEN) + ")"


def orden_seccion(seccion: str) -> int:
    """Posición de una sección para ordenar. Las desconocidas van al final."""
    try:
        return SECCIONES_ORDEN.index(seccion)
    except ValueError:
        return len(SECCIONES_ORDEN)
_TIPOS_CALCULO = "('POR_KG','POR_EMBARQUE','PORCENTAJE')"
_MODALIDADES = "('AEREA','MARITIMA','TERRESTRE')"
_MONEDAS = "('USD','COP')"
_ESTADOS_COT = "('BORRADOR','ENVIADA','APROBADA','RECHAZADA','VENCIDA')"
_ESTADOS_OPE = "('ABIERTA','EN_CURSO','CERRADA','CANCELADA')"
_ESTADOS_DOC = "('BORRADOR','EMITIDA','ANULADA')"
_ORIGEN_BL = "('RECIBIDO','EMITIDO')"      # importación recibe, exportación emite
_TIPO_CARGA = "('FCL','LCL')"
_PAGO_FLETE = "('PREPAID','COLLECT')"
_ESTADOS_DOC_OPE = "('PENDIENTE','RECIBIDO','APROBADO')"
_INCOTERMS = "('EXW','FCA','FAS','FOB','CFR','CIF','CPT','CIP','DAP','DPU','DDP')"


# ---------------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------------

class OpeAerolinea(Base):
    __tablename__ = "ope_aerolinea"
    __table_args__ = (
        CheckConstraint(f"modalidad IN {_MODALIDADES}", name="chk_aerolinea_modalidad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_iata: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    modalidad: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OpeAeropuerto(Base):
    __tablename__ = "ope_aeropuerto"
    __table_args__ = (
        CheckConstraint(f"modalidad IN {_MODALIDADES}", name="chk_aeropuerto_modalidad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_iata: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    pais: Mapped[str] = mapped_column(String(100), nullable=False)
    modalidad: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OpeConcepto(Base, AuditMixin):
    __tablename__ = "ope_concepto"
    __table_args__ = (
        CheckConstraint(f"seccion IN {_SECCIONES}", name="chk_concepto_seccion"),
        CheckConstraint(f"tipo_calculo IN {_TIPOS_CALCULO}", name="chk_concepto_tipo_calculo"),
        CheckConstraint(f"moneda IN {_MONEDAS}", name="chk_concepto_moneda"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    seccion: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_calculo: Mapped[str] = mapped_column(String(20), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    # FK a cnt_cuenta se agrega en Fase 1
    cuenta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    # Parámetros de facturación (una factura de venta se arma desde el concepto).
    cuenta_ingreso_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_devolucion_venta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    tarifa_iva_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_tarifa_iva.id"), nullable=True)
    um_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_unidad_medida.id"), nullable=True)
    es_valor_tercero: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))

    cuenta_ingreso: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_ingreso_id])
    cuenta_devolucion_venta: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_devolucion_venta_id])
    tarifa_iva: Mapped[Optional["AdmTarifaIva"]] = relationship("AdmTarifaIva", foreign_keys=[tarifa_iva_id])
    um: Mapped[Optional["InvUnidadMedida"]] = relationship("InvUnidadMedida", foreign_keys=[um_id])
    lineas: Mapped[list["OpeCotizacionLinea"]] = relationship("OpeCotizacionLinea", back_populates="concepto")
    # Retenciones que practica el cliente sobre este concepto. Es lista y no un
    # solo campo porque retefuente y reteICA conviven sobre la misma base.
    retenciones: Mapped[list["OpeConceptoRetencion"]] = relationship(
        "OpeConceptoRetencion", back_populates="concepto", cascade="all, delete-orphan")


class OpeConceptoRetencion(Base):
    """Retención parametrizada en un concepto operativo.

    Mismo patrón que `adm_concepto_retencion` para los conceptos de compras: al
    facturar, el sistema arma las retenciones agrupando por tarifa en vez de que
    el usuario las capture a mano.
    """
    __tablename__ = "ope_concepto_retencion"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concepto_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_concepto.id"), nullable=False)
    retencion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_retencion.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    concepto: Mapped["OpeConcepto"] = relationship("OpeConcepto", back_populates="retenciones")
    retencion: Mapped["AdmRetencion"] = relationship("AdmRetencion", foreign_keys=[retencion_id])


# ---------------------------------------------------------------------------
# Cotización
# ---------------------------------------------------------------------------

class OpeCotizacion(Base, AuditMixin):
    __tablename__ = "ope_cotizacion"
    __table_args__ = (
        CheckConstraint("tipo_operacion IN ('IMPORTACION','EXPORTACION')", name="chk_cotizacion_tipo_operacion"),
        CheckConstraint(f"modalidad IN {_MODALIDADES}", name="chk_cotizacion_modalidad"),
        CheckConstraint(f"estado IN {_ESTADOS_COT}", name="chk_cotizacion_estado"),
        CheckConstraint(f"moneda_mercancia IN {_MONEDAS}", name="chk_cotizacion_moneda_mercancia"),
        CheckConstraint(f"incoterm IN {_INCOTERMS}", name="chk_cotizacion_incoterm"),
        Index("idx_cotizacion_cliente", "cliente_id"),
        Index("idx_cotizacion_estado", "estado"),
        Index("idx_cotizacion_fecha", "fecha"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cliente_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vigencia: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_operacion: Mapped[str] = mapped_column(String(20), nullable=False)
    modalidad: Mapped[str] = mapped_column(String(20), default="AEREA", nullable=False)
    origen: Mapped[str] = mapped_column(String(200), nullable=False)
    destino: Mapped[str] = mapped_column(String(200), nullable=False)
    aerolinea_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aerolinea.id"), nullable=True)
    incoterm: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    piezas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    peso_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    valor_mercancia: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    moneda_mercancia: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    valor_cif: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    trm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR", nullable=False)

    asesor_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=True)
    # Una operación agrupa 1..N cotizaciones (consolidación de clientes).
    operacion_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=True, index=True)

    cliente: Mapped["AdmTercero"] = relationship("AdmTercero", foreign_keys=[cliente_id])
    aerolinea: Mapped[Optional["OpeAerolinea"]] = relationship("OpeAerolinea", foreign_keys=[aerolinea_id])
    lineas: Mapped[list["OpeCotizacionLinea"]] = relationship("OpeCotizacionLinea", back_populates="cotizacion", cascade="all, delete-orphan")
    operacion: Mapped[Optional["OpeOperacion"]] = relationship("OpeOperacion", foreign_keys=[operacion_id], back_populates="cotizaciones")


class OpeCotizacionLinea(Base):
    __tablename__ = "ope_cotizacion_linea"
    __table_args__ = (
        CheckConstraint(f"seccion IN {_SECCIONES}", name="chk_cot_linea_seccion"),
        CheckConstraint(f"tipo_calculo IN {_TIPOS_CALCULO}", name="chk_cot_linea_tipo_calculo"),
        CheckConstraint(f"moneda IN {_MONEDAS}", name="chk_cot_linea_moneda"),
        Index("idx_cot_linea_cotizacion", "cotizacion_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cotizacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_cotizacion.id"), nullable=False)
    seccion: Mapped[str] = mapped_column(String(50), nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    concepto_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_concepto.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_calculo: Mapped[str] = mapped_column(String(20), nullable=False)
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    base: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=1, nullable=False)
    minimo: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)          # de venta
    minimo_costo: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)    # del proveedor
    total_venta: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    total_costo: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    proveedor_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    valor_tercero: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))
    # Concepto que puede o no ejecutarse: se cotiza con su valor pero no suma
    # en la sección ni en el total. Solo entra a facturación si operación lo confirma.
    opcional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))
    condiciones_costo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cotizacion: Mapped["OpeCotizacion"] = relationship("OpeCotizacion", back_populates="lineas")
    concepto: Mapped[Optional["OpeConcepto"]] = relationship("OpeConcepto", back_populates="lineas")
    proveedor: Mapped[Optional["AdmTercero"]] = relationship("AdmTercero", foreign_keys=[proveedor_id])

    @property
    def proveedor_nombre(self) -> Optional[str]:
        return self.proveedor.razon_social if self.proveedor else None


# ---------------------------------------------------------------------------
# Operación (la carpeta)
# ---------------------------------------------------------------------------

class OpeOperacion(Base, AuditMixin):
    __tablename__ = "ope_operacion"
    __table_args__ = (
        CheckConstraint(f"estado IN {_ESTADOS_OPE}", name="chk_operacion_estado"),
        Index("idx_operacion_estado", "estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    fecha_apertura: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="ABIERTA", nullable=False)
    aerolinea_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aerolinea.id"), nullable=True)
    piezas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    peso_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)

    cotizaciones: Mapped[list["OpeCotizacion"]] = relationship("OpeCotizacion", foreign_keys="OpeCotizacion.operacion_id", back_populates="operacion")
    aerolinea: Mapped[Optional["OpeAerolinea"]] = relationship("OpeAerolinea", foreign_keys=[aerolinea_id])
    hawbs: Mapped[list["OpeHawb"]] = relationship("OpeHawb", back_populates="operacion", cascade="all, delete-orphan")
    mawbs: Mapped[list["OpeMawb"]] = relationship("OpeMawb", back_populates="operacion", cascade="all, delete-orphan")
    manifiestos: Mapped[list["OpeManifiesto"]] = relationship("OpeManifiesto", back_populates="operacion", cascade="all, delete-orphan")
    eventos: Mapped[list["OpeEvento"]] = relationship("OpeEvento", back_populates="operacion", cascade="all, delete-orphan")
    documentos: Mapped[list["OpeDocumento"]] = relationship("OpeDocumento", back_populates="operacion", cascade="all, delete-orphan")
    confirmaciones: Mapped[list["OpeConfirmacionLinea"]] = relationship("OpeConfirmacionLinea", back_populates="operacion", cascade="all, delete-orphan")
    # Marítimo — conviven con los aéreos: una operación puede ser multimodal.
    mbls: Mapped[list["OpeMbl"]] = relationship("OpeMbl", back_populates="operacion", cascade="all, delete-orphan")
    hbls: Mapped[list["OpeHbl"]] = relationship("OpeHbl", back_populates="operacion", cascade="all, delete-orphan")
    contenedores: Mapped[list["OpeContenedor"]] = relationship("OpeContenedor", back_populates="operacion", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Documentos de transporte aéreo
# ---------------------------------------------------------------------------

class OpeHawb(Base, AuditMixin):
    __tablename__ = "ope_hawb"
    __table_args__ = (
        CheckConstraint(f"estado IN {_ESTADOS_DOC}", name="chk_hawb_estado"),
        CheckConstraint("tipo_pago_flete IN ('PPD','COLL')", name="chk_hawb_tipo_pago_flete"),
        CheckConstraint("tipo_pago_otros IN ('PPD','COLL')", name="chk_hawb_tipo_pago_otros"),
        Index("idx_hawb_operacion", "operacion_id"),
        Index("idx_hawb_mawb", "mawb_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    mawb_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_mawb.id"), nullable=True)
    # Cliente/cotización a la que pertenece esta guía hija (consolidación).
    cotizacion_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_cotizacion.id"), nullable=True, index=True)
    numero_hawb: Mapped[str] = mapped_column(String(50), nullable=False)
    shipper_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    shipper_account: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    consignee_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    consignee_account: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    aeropuerto_origen_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aeropuerto.id"), nullable=True)
    aeropuerto_destino_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aeropuerto.id"), nullable=True)
    aerolinea_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aerolinea.id"), nullable=True)
    vuelo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fecha_vuelo: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    trm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    agent_iata_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    agent_account_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tipo_pago_flete: Mapped[str] = mapped_column(String(5), default="PPD", nullable=False)
    tipo_pago_otros: Mapped[str] = mapped_column(String(5), default="PPD", nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    valor_declarado_transporte: Mapped[str] = mapped_column(String(50), default="NVD", nullable=False)
    valor_declarado_aduana: Mapped[str] = mapped_column(String(50), default="NVD", nullable=False)
    monto_seguro: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    info_manejo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clase_tarifa: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    piezas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    peso_bruto_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    peso_cargable_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    tarifa: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    total_carga: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    descripcion_mercancia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dimensiones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cargo_peso: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cargo_valuacion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    otros_cargos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha_ejecucion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lugar_ejecucion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR", nullable=False)
    emitido_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    emitido_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    anulado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="hawbs")
    cotizacion: Mapped[Optional["OpeCotizacion"]] = relationship("OpeCotizacion", foreign_keys=[cotizacion_id])
    mawb: Mapped[Optional["OpeMawb"]] = relationship("OpeMawb", foreign_keys=[mawb_id], back_populates="hawbs")
    shipper: Mapped["AdmTercero"] = relationship("AdmTercero", foreign_keys=[shipper_id])
    consignee: Mapped["AdmTercero"] = relationship("AdmTercero", foreign_keys=[consignee_id])
    aerolinea: Mapped[Optional["OpeAerolinea"]] = relationship("OpeAerolinea", foreign_keys=[aerolinea_id])
    aeropuerto_origen: Mapped[Optional["OpeAeropuerto"]] = relationship("OpeAeropuerto", foreign_keys=[aeropuerto_origen_id])
    aeropuerto_destino: Mapped[Optional["OpeAeropuerto"]] = relationship("OpeAeropuerto", foreign_keys=[aeropuerto_destino_id])
    lineas_manifiesto: Mapped[list["OpeManifiestoLinea"]] = relationship("OpeManifiestoLinea", back_populates="hawb")


class OpeMawb(Base, AuditMixin):
    __tablename__ = "ope_mawb"
    __table_args__ = (
        CheckConstraint(f"estado IN {_ESTADOS_DOC}", name="chk_mawb_estado"),
        CheckConstraint(f"moneda_flete IN {_MONEDAS}", name="chk_mawb_moneda_flete"),
        CheckConstraint("tipo_pago_flete IN ('PPD','COLL')", name="chk_mawb_tipo_pago_flete"),
        CheckConstraint("tipo_pago_otros IN ('PPD','COLL')", name="chk_mawb_tipo_pago_otros"),
        Index("idx_mawb_operacion", "operacion_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    prefix: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    numero_mawb: Mapped[str] = mapped_column(String(50), nullable=False)
    consignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    shipper_account: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    consignee_account: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    aerolinea_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aerolinea.id"), nullable=True)
    aeropuerto_origen_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aeropuerto.id"), nullable=True)
    aeropuerto_destino_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aeropuerto.id"), nullable=True)
    vuelo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fecha_vuelo: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    trm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    agent_iata_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    agent_account_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tipo_pago_flete: Mapped[str] = mapped_column(String(5), default="PPD", nullable=False)
    tipo_pago_otros: Mapped[str] = mapped_column(String(5), default="PPD", nullable=False)
    moneda_flete: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    valor_declarado_transporte: Mapped[str] = mapped_column(String(50), default="NVD", nullable=False)
    valor_declarado_aduana: Mapped[str] = mapped_column(String(50), default="NVD", nullable=False)
    monto_seguro: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    info_manejo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clase_tarifa: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    piezas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    peso_bruto_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    peso_cargable_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    tarifa_por_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    descripcion_mercancia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dimensiones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flete_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    fsc: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    due_carrier: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    cargo_valuacion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    otros_due_agent: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    otros_due_carrier: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    total_prepaid: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    fecha_ejecucion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lugar_ejecucion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR", nullable=False)
    emitido_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    emitido_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    anulado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="mawbs")
    consignee: Mapped[Optional["AdmTercero"]] = relationship("AdmTercero", foreign_keys=[consignee_id])
    aerolinea: Mapped[Optional["OpeAerolinea"]] = relationship("OpeAerolinea", foreign_keys=[aerolinea_id])
    aeropuerto_origen: Mapped[Optional["OpeAeropuerto"]] = relationship("OpeAeropuerto", foreign_keys=[aeropuerto_origen_id])
    aeropuerto_destino: Mapped[Optional["OpeAeropuerto"]] = relationship("OpeAeropuerto", foreign_keys=[aeropuerto_destino_id])
    hawbs: Mapped[list["OpeHawb"]] = relationship("OpeHawb", foreign_keys="OpeHawb.mawb_id", back_populates="mawb")
    manifiestos: Mapped[list["OpeManifiesto"]] = relationship("OpeManifiesto", back_populates="mawb")


class OpeManifiesto(Base):
    __tablename__ = "ope_manifiesto"
    __table_args__ = (
        CheckConstraint(f"estado IN {_ESTADOS_DOC}", name="chk_manifiesto_estado"),
        Index("idx_manifiesto_operacion", "operacion_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    mawb_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_mawb.id"), nullable=False)
    aerolinea_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aerolinea.id"), nullable=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR", nullable=False)
    emitido_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    emitido_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    anulado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="manifiestos")
    mawb: Mapped["OpeMawb"] = relationship("OpeMawb", back_populates="manifiestos")
    aerolinea: Mapped[Optional["OpeAerolinea"]] = relationship("OpeAerolinea", foreign_keys=[aerolinea_id])
    lineas: Mapped[list["OpeManifiestoLinea"]] = relationship("OpeManifiestoLinea", back_populates="manifiesto", cascade="all, delete-orphan")


class OpeManifiestoLinea(Base):
    __tablename__ = "ope_manifiesto_linea"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manifiesto_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_manifiesto.id"), nullable=False)
    hawb_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_hawb.id"), nullable=False)
    exportador_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    importador_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    piezas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    peso_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    manifiesto: Mapped["OpeManifiesto"] = relationship("OpeManifiesto", back_populates="lineas")
    hawb: Mapped["OpeHawb"] = relationship("OpeHawb", back_populates="lineas_manifiesto")
    exportador: Mapped["AdmTercero"] = relationship("AdmTercero", foreign_keys=[exportador_id])
    importador: Mapped["AdmTercero"] = relationship("AdmTercero", foreign_keys=[importador_id])


# ---------------------------------------------------------------------------
# Bitácora y documentos requeridos
# ---------------------------------------------------------------------------

class OpeEvento(Base):
    __tablename__ = "ope_evento"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('STATUS','DOCUMENTO_RECIBIDO','NOTA','RESERVA','APERTURA','CIERRE')",
            name="chk_evento_tipo",
        ),
        Index("idx_evento_operacion", "operacion_id"),
        Index("idx_evento_fecha", "fecha_hora"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    # Evento dirigido a un HAWB (cliente) específico; null = evento de operación.
    hawb_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_hawb.id"), nullable=True, index=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    notificado_cliente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="eventos")
    hawb: Mapped[Optional["OpeHawb"]] = relationship("OpeHawb", foreign_keys=[hawb_id])


class OpeDocumento(Base):
    __tablename__ = "ope_documento"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('FACTURA_COMERCIAL','LISTA_EMPAQUE','CERTIFICADO_ORIGEN','OTRO')",
            name="chk_documento_tipo",
        ),
        CheckConstraint(f"estado IN {_ESTADOS_DOC_OPE}", name="chk_documento_estado"),
        Index("idx_documento_operacion", "operacion_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", nullable=False)
    fecha_recepcion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    archivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="documentos")


# ---------------------------------------------------------------------------
# Documentos de transporte marítimo
#
# Calca la jerarquía del aéreo (MAWB→HAWB) pero los datos no se parecen, por eso
# van en tablas propias: contenedor, CBM, tara y puertos no caben en ope_hawb.
# Naviera y puertos salen de ope_aerolinea/ope_aeropuerto con modalidad
# MARITIMA — esos catálogos ya nacieron multimodales.
# ---------------------------------------------------------------------------

class OpeMbl(Base, AuditMixin):
    """Bill of Lading maestro. Lo emite la naviera; Universal Cargo lo recibe."""

    __tablename__ = "ope_mbl"
    __table_args__ = (
        CheckConstraint(f"tipo_carga IN {_TIPO_CARGA}", name="chk_mbl_tipo_carga"),
        CheckConstraint(f"tipo_pago_flete IN {_PAGO_FLETE}", name="chk_mbl_pago_flete"),
        Index("idx_mbl_operacion", "operacion_id"),
        Index("idx_mbl_numero", "numero_bl"),
        Index("idx_mbl_booking", "booking_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    naviera_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aerolinea.id"), nullable=True)

    numero_bl: Mapped[str] = mapped_column(String(50), nullable=False)
    booking_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    export_references: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    referencia_cliente: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    # Partes
    shipper_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    shipper_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    consignee_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notify_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    notify_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agente_destino: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ruta
    pre_carriage_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    place_of_receipt: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    puerto_embarque_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aeropuerto.id"), nullable=True)
    puerto_descarga_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aeropuerto.id"), nullable=True)
    place_of_delivery: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    onward_inland_routing: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    buque: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    viaje: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    # Fechas — las de tracking no vienen en el BL pero sin ellas no se hace
    # seguimiento, que es lo que más usan (dos o tres veces por semana).
    fecha_emision: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lugar_emision: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    shipped_on_board: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    etd: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    eta: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_arribo: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Condiciones
    termino: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)      # CY-CY, CY-CFS…
    tipo_carga: Mapped[str] = mapped_column(String(5), default="FCL", nullable=False)
    tipo_pago_flete: Mapped[str] = mapped_column(String(10), default="PREPAID", nullable=False)
    freight_to_be_paid_at: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    num_originales: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    declared_value: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    free_days: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Carga
    say_total: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    marcas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    descripcion_mercancia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bultos_cantidad: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bultos_clase: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    carrier_receipt: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    peso_bruto_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    tara_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    cbm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)

    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="mbls")
    naviera: Mapped[Optional["OpeAerolinea"]] = relationship("OpeAerolinea", foreign_keys=[naviera_id])
    hbls: Mapped[list["OpeHbl"]] = relationship("OpeHbl", back_populates="mbl")
    contenedores: Mapped[list["OpeContenedor"]] = relationship("OpeContenedor", back_populates="mbl")


class OpeHbl(Base, AuditMixin):
    """Bill of Lading hijo. RECIBIDO del agente en importación; EMITIDO por
    Universal Cargo en exportación — por eso tiene ciclo de vida propio."""

    __tablename__ = "ope_hbl"
    __table_args__ = (
        CheckConstraint(f"origen IN {_ORIGEN_BL}", name="chk_hbl_origen"),
        CheckConstraint(f"estado IN {_ESTADOS_DOC}", name="chk_hbl_estado"),
        CheckConstraint(f"tipo_carga IN {_TIPO_CARGA}", name="chk_hbl_tipo_carga"),
        CheckConstraint(f"tipo_pago_flete IN {_PAGO_FLETE}", name="chk_hbl_pago_flete"),
        Index("idx_hbl_operacion", "operacion_id"),
        Index("idx_hbl_mbl", "mbl_id"),
        Index("idx_hbl_numero", "numero_hbl"),
        Index("idx_hbl_booking", "booking_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    mbl_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_mbl.id"), nullable=True)
    # Cliente/cotización al que pertenece esta casa, igual que en la HAWB.
    cotizacion_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_cotizacion.id"), nullable=True, index=True)

    origen: Mapped[str] = mapped_column(String(10), default="RECIBIDO", nullable=False)
    # Quién lo emitió cuando es RECIBIDO (el agente en origen, ej. KCS).
    emisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    emisor_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    numero_hbl: Mapped[str] = mapped_column(String(50), nullable=False)
    booking_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    export_references: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    referencia_cliente: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    do_numero: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    shipper_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    shipper_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    consignee_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # "TO ORDER" hace el BL negociable: no es un tercero, es una condición.
    consignee_a_la_orden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))
    notify_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    notify_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agente_entrega: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    pre_carriage_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    place_of_receipt: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    puerto_embarque_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aeropuerto.id"), nullable=True)
    puerto_descarga_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_aeropuerto.id"), nullable=True)
    place_of_delivery: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    onward_inland_routing: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    buque: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    viaje: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    fecha_emision: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lugar_emision: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    shipped_on_board: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    etd: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    eta: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_arribo: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    termino: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tipo_carga: Mapped[str] = mapped_column(String(5), default="FCL", nullable=False)
    tipo_pago_flete: Mapped[str] = mapped_column(String(10), default="PREPAID", nullable=False)
    freight_to_be_paid_at: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    num_originales: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    declared_value: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    say_total: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    marcas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    descripcion_mercancia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bultos_cantidad: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bultos_clase: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    carrier_receipt: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    peso_bruto_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    cbm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)

    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR", nullable=False)
    emitido_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    emitido_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    anulado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="hbls")
    mbl: Mapped[Optional["OpeMbl"]] = relationship("OpeMbl", back_populates="hbls")
    cotizacion: Mapped[Optional["OpeCotizacion"]] = relationship("OpeCotizacion", foreign_keys=[cotizacion_id])
    contenedores: Mapped[list["OpeHblContenedor"]] = relationship(
        "OpeHblContenedor", back_populates="hbl", cascade="all, delete-orphan")
    cargos: Mapped[list["OpeBlCargo"]] = relationship(
        "OpeBlCargo", back_populates="hbl", cascade="all, delete-orphan",
        order_by="OpeBlCargo.orden")


class OpeContenedor(Base, AuditMixin):
    """Contenedor físico. Va aparte porque un HBL puede amparar varios y un
    contenedor puede llevar varios HBL (LCL)."""

    __tablename__ = "ope_contenedor"
    __table_args__ = (
        Index("idx_contenedor_operacion", "operacion_id"),
        Index("idx_contenedor_numero", "numero"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    mbl_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_mbl.id"), nullable=True)

    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    sello: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)   # 20GP, 20ST, 40HC, 40RH…
    tara_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    peso_bruto_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    cbm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    # Los free days se negocian y hoy se anotan a mano en las notas de la cotización.
    fecha_devolucion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="contenedores")
    mbl: Mapped[Optional["OpeMbl"]] = relationship("OpeMbl", back_populates="contenedores")
    hbls: Mapped[list["OpeHblContenedor"]] = relationship(
        "OpeHblContenedor", back_populates="contenedor", cascade="all, delete-orphan")


class OpeHblContenedor(Base):
    """Puente N:M. Lleva cifras propias porque en LCL cada HBL aporta su parte
    de piezas, peso y volumen dentro del mismo contenedor."""

    __tablename__ = "ope_hbl_contenedor"
    __table_args__ = (
        UniqueConstraint("hbl_id", "contenedor_id", name="uq_hbl_contenedor"),
        Index("idx_hbl_cont_hbl", "hbl_id"),
        Index("idx_hbl_cont_contenedor", "contenedor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hbl_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_hbl.id"), nullable=False)
    contenedor_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_contenedor.id"), nullable=False)
    piezas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    peso_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    cbm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)

    hbl: Mapped["OpeHbl"] = relationship("OpeHbl", back_populates="contenedores")
    contenedor: Mapped["OpeContenedor"] = relationship("OpeContenedor", back_populates="hbls")


class OpeBlCargo(Base):
    """Cuadro Freight & Charges del BL. Es tabla y no un flag porque al emitir
    el HBL el flete se imprime desglosado."""

    __tablename__ = "ope_bl_cargo"
    __table_args__ = (
        CheckConstraint(f"pago IN {_PAGO_FLETE}", name="chk_bl_cargo_pago"),
        Index("idx_bl_cargo_hbl", "hbl_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hbl_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_hbl.id"), nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    concepto: Mapped[str] = mapped_column(String(120), nullable=False)
    tarifa: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    unidad: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    moneda: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    valor: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    pago: Mapped[str] = mapped_column(String(10), default="PREPAID", nullable=False)

    hbl: Mapped["OpeHbl"] = relationship("OpeHbl", back_populates="cargos")


# ---------------------------------------------------------------------------
# Confirmación de la operación sobre lo cotizado
# ---------------------------------------------------------------------------

class OpeConfirmacionLinea(Base, AuditMixin):
    """Lo que operación confirma que se ejecutó, contra lo que comercial cotizó.

    La cotización es un documento comercial y no se muta: los valores realmente
    ejecutados viven aquí. Solo lo confirmado es facturable.
    """

    __tablename__ = "ope_confirmacion_linea"
    __table_args__ = (
        UniqueConstraint("operacion_id", "cotizacion_linea_id", name="uq_confirmacion_operacion_linea"),
        Index("idx_confirmacion_operacion", "operacion_id"),
        Index("idx_confirmacion_linea", "cotizacion_linea_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operacion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_operacion.id"), nullable=False)
    cotizacion_linea_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ope_cotizacion_linea.id"), nullable=False)

    confirmado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=text("false"))
    # Peso/base realmente ejecutado. Solo mueve el total en líneas POR_KG.
    base_confirmada: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=1, nullable=False)
    valor_unitario_confirmado: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    costo_unitario_confirmado: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    total_venta_confirmado: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    # Solo estadística y margen real — no alimenta CxP.
    total_costo_confirmado: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)

    confirmado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=True)
    confirmado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    operacion: Mapped["OpeOperacion"] = relationship("OpeOperacion", back_populates="confirmaciones")
    linea: Mapped["OpeCotizacionLinea"] = relationship("OpeCotizacionLinea")

