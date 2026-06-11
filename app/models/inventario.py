from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


class InvBodega(Base, AuditMixin):
    __tablename__ = "inv_bodega"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsable_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=True
    )
    responsable: Mapped[Optional["AdmUsuario"]] = relationship("AdmUsuario", foreign_keys=[responsable_id])


class InvFamilia(Base, AuditMixin):
    __tablename__ = "inv_familia"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cuenta_inventario_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_costo_ventas_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ingreso_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_devolucion_venta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_devolucion_compra_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ajuste_entrada_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ajuste_salida_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)


class InvUnidadMedida(Base):
    __tablename__ = "inv_unidad_medida"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class InvTipoProducto(Base):
    __tablename__ = "inv_tipo_producto"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    maneja_inventario: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cuenta_inventario_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_costo_ventas_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ingreso_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_devolucion_venta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_devolucion_compra_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ajuste_entrada_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ajuste_salida_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    modificado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    modificado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)


class InvProducto(Base, AuditMixin):
    __tablename__ = "inv_producto"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tipo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_tipo_producto.id"), nullable=False)
    familia_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_familia.id"), nullable=True)
    um_base_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_unidad_medida.id"), nullable=False)
    maneja_inventario: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    maneja_series: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    maneja_lotes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tiene_variantes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cuenta_inventario_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_costo_ventas_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ingreso_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_devolucion_venta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_devolucion_compra_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ajuste_entrada_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ajuste_salida_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)

    tipo: Mapped["InvTipoProducto"] = relationship("InvTipoProducto", foreign_keys=[tipo_id])
    familia: Mapped[Optional["InvFamilia"]] = relationship("InvFamilia", foreign_keys=[familia_id])
    um_base: Mapped["InvUnidadMedida"] = relationship("InvUnidadMedida", foreign_keys=[um_base_id])


class InvProductoUm(Base):
    __tablename__ = "inv_producto_um"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    producto_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_producto.id"), nullable=False)
    um_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("inv_unidad_medida.id"), nullable=False)
    factor: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    es_compra: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    es_venta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    um: Mapped["InvUnidadMedida"] = relationship("InvUnidadMedida", foreign_keys=[um_id])
