from decimal import Decimal
from typing import Any, Optional
import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, SmallInteger, String
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
