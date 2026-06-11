from datetime import datetime, date
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey,
    Numeric, String, Text, UniqueConstraint, func
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


class CxcDocumento(Base, AuditMixin):
    __tablename__ = "cxc_documento"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_cxc_numero"),
        CheckConstraint("tipo IN ('FACTURA','RECIBO','NOTA_CREDITO','NOTA_DEBITO','ANTICIPO')", name="chk_cxc_tipo"),
        CheckConstraint("estado IN ('borrador','contabilizado','anulado')", name="chk_cxc_estado"),
        CheckConstraint("saldo >= 0", name="chk_cxc_saldo"),
        CheckConstraint("total >= 0", name="chk_cxc_total"),
        CheckConstraint(
            "tipo NOT IN ('FACTURA','NOTA_DEBITO') OR fecha_vencimiento IS NOT NULL",
            name="chk_cxc_vencimiento"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_periodo.id"), nullable=False)
    tercero_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=False)
    moneda_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_moneda.id"), nullable=False)
    trm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_iva: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_retenciones: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    saldo: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)
    asiento_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_asiento.id"), nullable=True)
    tarifa_iva_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_tarifa_iva.id"), nullable=True)
    condicion_pago_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_condicion_pago.id"), nullable=True)
    asiento_modificado_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    origen_modulo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    origen_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    documento_origen_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxc_documento.id"), nullable=True)
    ban_cuenta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ban_cuenta.id"), nullable=True)

    retenciones: Mapped[list["CxcRetencion"]] = relationship("CxcRetencion", back_populates="documento", cascade="all, delete-orphan")
    documento_origen: Mapped[Optional["CxcDocumento"]] = relationship("CxcDocumento", remote_side="CxcDocumento.id")


class CxcRetencion(Base):
    __tablename__ = "cxc_retencion"
    __table_args__ = (
        CheckConstraint("tipo IN ('RETEFUENTE','RETEICA','RETEIVA')", name="chk_cxc_ret_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    documento_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxc_documento.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    concepto: Mapped[str] = mapped_column(String(100), nullable=False)
    base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=False)

    documento: Mapped["CxcDocumento"] = relationship("CxcDocumento", back_populates="retenciones")


class CxcParametroContable(Base):
    __tablename__ = "cxc_parametro_contable"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_clientes_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ingresos_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_iva_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    modificado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    modificado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)


class CxcAplicacion(Base):
    __tablename__ = "cxc_aplicacion"
    __table_args__ = (
        CheckConstraint("valor > 0", name="chk_cxc_app_valor"),
        CheckConstraint("documento_credito_id <> documento_debito_id", name="chk_cxc_app_distintos"),
        CheckConstraint("estado IN ('pendiente','aplicado')", name="chk_cxc_app_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    documento_credito_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxc_documento.id"), nullable=False)
    documento_debito_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxc_documento.id"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), default="aplicado", nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)
