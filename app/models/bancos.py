from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
import uuid

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


class BanBanco(Base, AuditMixin):
    __tablename__ = "ban_banco"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    codigo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Configuración para importación de extractos
    formato: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    mapeo_columnas: Mapped[Optional[Any]] = mapped_column(pg.JSONB, nullable=True)
    fila_inicio: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    formato_fecha: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cuentas: Mapped[list["BanCuenta"]] = relationship("BanCuenta", back_populates="banco")


class BanCuenta(Base, AuditMixin):
    __tablename__ = "ban_cuenta"
    __table_args__ = (
        CheckConstraint("tipo IN ('CORRIENTE','AHORRO')", name="chk_ban_cuenta_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    banco_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ban_banco.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    moneda_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_moneda.id"), nullable=True)
    cuenta_contable_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    banco: Mapped["BanBanco"] = relationship("BanBanco", back_populates="cuentas")
    moneda: Mapped[Optional["AdmMoneda"]] = relationship("AdmMoneda", foreign_keys=[moneda_id])
    cuenta_contable: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_contable_id])
    chequeras: Mapped[list["BanChequera"]] = relationship("BanChequera", back_populates="cuenta")


class BanChequera(Base, AuditMixin):
    __tablename__ = "ban_chequera"
    __table_args__ = (
        CheckConstraint("estado IN ('ACTIVA','AGOTADA','ANULADA')", name="chk_ban_chequera_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ban_cuenta.id"), nullable=False)
    prefijo: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    numero_desde: Mapped[int] = mapped_column(nullable=False)
    numero_hasta: Mapped[int] = mapped_column(nullable=False)
    consecutivo_actual: Mapped[int] = mapped_column(nullable=False)
    estado: Mapped[str] = mapped_column(String(10), default="ACTIVA", nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cuenta: Mapped["BanCuenta"] = relationship("BanCuenta", back_populates="chequeras")


class BanTransferencia(Base, AuditMixin):
    __tablename__ = "ban_transferencia"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_ban_transf_numero"),
        CheckConstraint("estado IN ('borrador','contabilizado','anulado')", name="chk_ban_transf_estado"),
        CheckConstraint("cuenta_origen_id <> cuenta_destino_id", name="chk_ban_transf_distintas"),
        CheckConstraint("valor > 0", name="chk_ban_transf_valor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_periodo.id"), nullable=False)
    cuenta_origen_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ban_cuenta.id"), nullable=False)
    cuenta_destino_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ban_cuenta.id"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)
    asiento_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_asiento.id"), nullable=True)

    cuenta_origen: Mapped["BanCuenta"] = relationship("BanCuenta", foreign_keys=[cuenta_origen_id])
    cuenta_destino: Mapped["BanCuenta"] = relationship("BanCuenta", foreign_keys=[cuenta_destino_id])


class BanExtracto(Base, AuditMixin):
    """Extracto bancario cargado para conciliar contra el libro de la cuenta."""
    __tablename__ = "ban_extracto"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ban_cuenta.id"), nullable=False)
    fecha_desde: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    saldo_final: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="abierta", nullable=False)  # abierta | cerrada

    cuenta: Mapped["BanCuenta"] = relationship("BanCuenta", foreign_keys=[cuenta_id])
    lineas: Mapped[list["BanExtractoLinea"]] = relationship(
        "BanExtractoLinea", back_populates="extracto", cascade="all, delete-orphan",
        order_by="BanExtractoLinea.fecha",
    )


class BanExtractoLinea(Base):
    __tablename__ = "ban_extracto_linea"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extracto_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("ban_extracto.id", ondelete="CASCADE"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(300), nullable=False)
    referencia: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # valor con signo desde la perspectiva de la cuenta: + entra (crédito banco), − sale (débito banco)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    conciliado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    asiento_linea_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_asiento_linea.id"), nullable=True)
    conciliado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    conciliado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)

    extracto: Mapped["BanExtracto"] = relationship("BanExtracto", back_populates="lineas")
