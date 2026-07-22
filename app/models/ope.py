from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


_SECCIONES = "('TRANSPORTE_INTERNACIONAL','GASTOS_ORIGEN','GASTOS_DESTINO','ADUANA','TRANSPORTE_TERRESTRE','ALMACENAMIENTO','SEGURO')"
_TIPOS_CALCULO = "('POR_KG','POR_EMBARQUE','PORCENTAJE')"
_MODALIDADES = "('AEREA','MARITIMA','TERRESTRE')"
_MONEDAS = "('USD','COP')"
_ESTADOS_COT = "('BORRADOR','ENVIADA','APROBADA','RECHAZADA','VENCIDA')"
_ESTADOS_OPE = "('ABIERTA','EN_CURSO','CERRADA','CANCELADA')"
_ESTADOS_DOC = "('BORRADOR','EMITIDA','ANULADA')"
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

    lineas: Mapped[list["OpeCotizacionLinea"]] = relationship("OpeCotizacionLinea", back_populates="concepto")


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
    minimo: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    total_venta: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    total_costo: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    proveedor_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    condiciones_costo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cotizacion: Mapped["OpeCotizacion"] = relationship("OpeCotizacion", back_populates="lineas")
    concepto: Mapped[Optional["OpeConcepto"]] = relationship("OpeConcepto", back_populates="lineas")
    proveedor: Mapped[Optional["AdmTercero"]] = relationship("AdmTercero", foreign_keys=[proveedor_id])


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

