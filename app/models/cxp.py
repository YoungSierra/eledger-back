from datetime import datetime, date
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey,
    Numeric, SmallInteger, String, Text, UniqueConstraint, func
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


class CxpParametroContable(Base):
    __tablename__ = "cxp_parametro_contable"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_proveedores_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_mercancias_recibidas_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    modificado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    modificado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)


class CxpDocumento(Base, AuditMixin):
    __tablename__ = "cxp_documento"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_cxp_numero"),
        CheckConstraint("tipo IN ('FACTURA','COMPROBANTE','NOTA_CREDITO','NOTA_DEBITO','ANTICIPO')", name="chk_cxp_tipo"),
        CheckConstraint("estado IN ('borrador','contabilizado','anulado')", name="chk_cxp_estado"),
        CheckConstraint("saldo >= 0", name="chk_cxp_saldo"),
        CheckConstraint("total >= 0", name="chk_cxp_total"),
        CheckConstraint(
            "tipo NOT IN ('FACTURA','NOTA_DEBITO') OR fecha_vencimiento IS NOT NULL",
            name="chk_cxp_vencimiento"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_proveedor: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
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
    condicion_pago_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_condicion_pago.id"), nullable=True)
    ban_cuenta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ban_cuenta.id"), nullable=True)
    asiento_modificado_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    origen_modulo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    origen_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    documento_origen_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxp_documento.id"), nullable=True)

    lineas: Mapped[list["CxpDocumentoLinea"]] = relationship(
        "CxpDocumentoLinea", back_populates="documento", cascade="all, delete-orphan",
        order_by="CxpDocumentoLinea.orden",
    )
    documento_origen: Mapped[Optional["CxpDocumento"]] = relationship("CxpDocumento", remote_side="CxpDocumento.id")


class CxpDocumentoLinea(Base):
    __tablename__ = "cxp_documento_linea"
    __table_args__ = (
        CheckConstraint("concepto_id IS NOT NULL OR cuenta_id IS NOT NULL", name="chk_cxp_linea_cuenta"),
        CheckConstraint("subtotal > 0", name="chk_cxp_linea_subtotal"),
        CheckConstraint("iva_tipo IN ('GRAVADO_19','GRAVADO_5','EXCLUIDO','EXENTO','INC','NINGUNO')", name="chk_cxp_linea_iva_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    documento_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxp_documento.id", ondelete="CASCADE"), nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(300), nullable=False)
    concepto_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_concepto.id"), nullable=True)
    cuenta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    iva_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    total_iva: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    centro_costo_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_centro_costo.id"), nullable=True)
    iva_tipo: Mapped[str] = mapped_column(String(20), default="NINGUNO", nullable=False)
    cuenta_iva_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)

    documento: Mapped["CxpDocumento"] = relationship("CxpDocumento", back_populates="lineas")
    retenciones: Mapped[list["CxpLineaRetencion"]] = relationship(
        "CxpLineaRetencion", back_populates="linea", cascade="all, delete-orphan"
    )


class CxpLineaRetencion(Base):
    __tablename__ = "cxp_linea_retencion"
    __table_args__ = (
        CheckConstraint("tipo IN ('RETEFUENTE','RETEICA','RETEIVA')", name="chk_cxp_lret_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    linea_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxp_documento_linea.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(100), nullable=False)
    base: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cuenta_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)

    linea: Mapped["CxpDocumentoLinea"] = relationship("CxpDocumentoLinea", back_populates="retenciones")


class CxpAplicacion(Base):
    __tablename__ = "cxp_aplicacion"
    __table_args__ = (
        CheckConstraint("valor > 0", name="chk_cxp_app_valor"),
        CheckConstraint("documento_credito_id <> documento_debito_id", name="chk_cxp_app_distintos"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    documento_credito_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxp_documento.id"), nullable=False)
    documento_debito_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cxp_documento.id"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), default="aplicado", nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)
