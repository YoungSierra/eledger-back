from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


class ComOrdenCompra(Base, AuditMixin):
    __tablename__ = "com_orden_compra"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_oc_numero"),
        CheckConstraint(
            "estado IN ('borrador','aprobada','en_proceso','recibida_total','anulada')",
            name="chk_oc_estado",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_entrega_esperada: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_periodo.id"), nullable=False)
    proveedor_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    moneda_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_moneda.id"), nullable=False)
    trm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_iva: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)
    aprobado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=True)
    aprobado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    proveedor: Mapped["AdmTercero"] = relationship("AdmTercero", foreign_keys=[proveedor_id])
    moneda: Mapped["AdmMoneda"] = relationship("AdmMoneda", foreign_keys=[moneda_id])
    lineas: Mapped[list["ComOcLinea"]] = relationship("ComOcLinea", back_populates="oc", cascade="all, delete-orphan")


class ComOcLinea(Base):
    __tablename__ = "com_oc_linea"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_oc_cantidad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oc_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("com_orden_compra.id"), nullable=False)
    producto_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_producto.id"), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    um_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_unidad_medida.id"), nullable=False)
    cantidad_base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    descuento_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    iva_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    total_iva: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tarifa_iva_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_tarifa_iva.id"), nullable=True)
    centro_costo_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_centro_costo.id"), nullable=True)
    cantidad_recibida: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)

    oc: Mapped["ComOrdenCompra"] = relationship("ComOrdenCompra", back_populates="lineas")
    producto: Mapped["InvProducto"] = relationship("InvProducto", foreign_keys=[producto_id])
    um: Mapped["InvUnidadMedida"] = relationship("InvUnidadMedida", foreign_keys=[um_id])
    tarifa_iva: Mapped[Optional["AdmTarifaIva"]] = relationship("AdmTarifaIva", foreign_keys=[tarifa_iva_id])
    centro_costo: Mapped[Optional["CntCentroCosto"]] = relationship("CntCentroCosto", foreign_keys=[centro_costo_id])


class ComRecepcion(Base, AuditMixin):
    __tablename__ = "com_recepcion"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_recepcion_numero"),
        CheckConstraint(
            "estado IN ('borrador','confirmada','anulada')",
            name="chk_recepcion_estado",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_periodo.id"), nullable=False)
    oc_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("com_orden_compra.id"), nullable=False)
    bodega_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_bodega.id"), nullable=False)
    proveedor_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)
    movimiento_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_movimiento.id"), nullable=True)
    asiento_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_asiento.id"), nullable=True)

    oc: Mapped["ComOrdenCompra"] = relationship("ComOrdenCompra", foreign_keys=[oc_id])
    bodega: Mapped["InvBodega"] = relationship("InvBodega", foreign_keys=[bodega_id])
    proveedor: Mapped["AdmTercero"] = relationship("AdmTercero", foreign_keys=[proveedor_id])
    lineas: Mapped[list["ComRecepcionLinea"]] = relationship("ComRecepcionLinea", back_populates="recepcion", cascade="all, delete-orphan")


class ComRecepcionLinea(Base):
    __tablename__ = "com_recepcion_linea"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_recep_cantidad"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recepcion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("com_recepcion.id"), nullable=False)
    oc_linea_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("com_oc_linea.id"), nullable=False)
    producto_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_producto.id"), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    um_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_unidad_medida.id"), nullable=False)
    cantidad_base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    recepcion: Mapped["ComRecepcion"] = relationship("ComRecepcion", back_populates="lineas")
    oc_linea: Mapped["ComOcLinea"] = relationship("ComOcLinea", foreign_keys=[oc_linea_id])
    producto: Mapped["InvProducto"] = relationship("InvProducto", foreign_keys=[producto_id])
    um: Mapped["InvUnidadMedida"] = relationship("InvUnidadMedida", foreign_keys=[um_id])
