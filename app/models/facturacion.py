from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin

# Tabla de vínculo factura ↔ remisiones (muchos a muchos)
fac_factura_remision = Table(
    "fac_factura_remision",
    Base.metadata,
    Column("factura_id", ForeignKey("fac_factura.id"), primary_key=True),
    Column("remision_id", ForeignKey("inv_remision.id"), primary_key=True),
)


class FacResolucion(Base, AuditMixin):
    __tablename__ = "fac_resolucion"
    __table_args__ = (
        CheckConstraint("tipo IN ('FACTURA_VENTA','NOTA_CREDITO','NOTA_DEBITO')", name="chk_resolucion_tipo"),
        UniqueConstraint("prefijo", "tipo", name="uq_resolucion_prefijo_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="FACTURA_VENTA")
    numero_resolucion: Mapped[str] = mapped_column(String(50), nullable=False)
    prefijo: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    rango_desde: Mapped[int] = mapped_column(Integer, nullable=False)
    rango_hasta: Mapped[int] = mapped_column(Integer, nullable=False)
    consecutivo_actual: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fecha_desde: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FacFactura(Base, AuditMixin):
    __tablename__ = "fac_factura"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_fac_factura_numero"),
        CheckConstraint("estado IN ('borrador','contabilizada','anulada')", name="chk_fac_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_periodo.id"), nullable=False)
    cliente_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    moneda_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_moneda.id"), nullable=False)
    trm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    condicion_pago_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_condicion_pago.id"), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_descuentos: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_iva: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_retenciones: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)
    asiento_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_asiento.id"), nullable=True)
    asiento_modificado_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cxc_documento_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxc_documento.id"), nullable=True)
    bodega_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_bodega.id"), nullable=True)
    cufe: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    fecha_dian: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dian_estado: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    lineas: Mapped[list["FacFacturaLinea"]] = relationship(
        "FacFacturaLinea", back_populates="factura", cascade="all, delete-orphan",
        order_by="FacFacturaLinea.orden",
    )
    retenciones: Mapped[list["FacFacturaRetencion"]] = relationship(
        "FacFacturaRetencion", back_populates="factura", cascade="all, delete-orphan",
    )
    remisiones: Mapped[list["InvRemision"]] = relationship(
        "InvRemision", secondary=fac_factura_remision, viewonly=False,
    )


class FacFacturaLinea(Base):
    __tablename__ = "fac_factura_linea"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_fac_linea_cantidad"),
        CheckConstraint("iva_tipo IN ('GRAVADO_19','GRAVADO_5','EXCLUIDO','EXENTO','INC','NINGUNO')", name="chk_fac_linea_iva_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factura_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("fac_factura.id"), nullable=False)
    producto_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_producto.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(300), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    um_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_unidad_medida.id"), nullable=True)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    descuento_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    descuento_valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    iva_tipo: Mapped[str] = mapped_column(String(20), default="NINGUNO", nullable=False)
    iva_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    total_iva: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    cuenta_iva_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cuenta_ingreso_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    centro_costo_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_centro_costo.id"), nullable=True)
    remision_linea_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_remision_linea.id"), nullable=True)
    orden: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)

    factura: Mapped["FacFactura"] = relationship("FacFactura", back_populates="lineas")


class FacFacturaRetencion(Base):
    __tablename__ = "fac_factura_retencion"
    __table_args__ = (
        CheckConstraint("tipo IN ('RETEFUENTE','RETEICA','RETEIVA')", name="chk_fac_ret_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factura_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("fac_factura.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    concepto: Mapped[str] = mapped_column(String(100), nullable=False)
    base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=False)

    factura: Mapped["FacFactura"] = relationship("FacFactura", back_populates="retenciones")


class FacConfigElectronica(Base, AuditMixin):
    """
    Configuración del proveedor de facturación electrónica. Fila única por empresa
    (una empresa = una BD). Ver docs/modelos/datos/fase-4-esquema.md:170.

    `credenciales` es JSONB porque cada proveedor pide campos distintos:
    Dataico usa {account_id, auth_token}. El token va ENCRIPTADO (Fernet) desde
    el service — nunca en claro en la BD ni en las respuestas de la API.
    """
    __tablename__ = "fac_config_electronica"
    __table_args__ = (
        CheckConstraint(
            "proveedor IN ('DATAICO','PTH_APIFE','PTH_SIECOM','PTH_FACTUS','DIAN_DIRECTO')",
            name="chk_config_electronica_proveedor",
        ),
        CheckConstraint("ambiente IN ('PRUEBAS','PRODUCCION')", name="chk_config_electronica_ambiente"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proveedor: Mapped[str] = mapped_column(String(30), nullable=False)
    # Nombre comercial del PTH que se imprime en el pie de la factura. Vive aquí
    # y no en adm_configuracion para no partir la config del proveedor en dos.
    nombre_pth: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    credenciales: Mapped[dict] = mapped_column(pg.JSONB, nullable=False, default=dict)
    ambiente: Mapped[str] = mapped_column(String(20), nullable=False, default="PRUEBAS")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
