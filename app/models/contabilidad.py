from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index,
    Numeric, Sequence, SmallInteger, String, Text, UniqueConstraint, func
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


class CntPeriodo(Base, AuditMixin):
    __tablename__ = "cnt_periodo"
    __table_args__ = (
        UniqueConstraint("anio", "mes", name="uq_periodo_anio_mes"),
        CheckConstraint("mes BETWEEN 1 AND 12", name="chk_mes_valido"),
        CheckConstraint("fecha_cierre >= fecha_inicio", name="chk_fechas_periodo"),
        CheckConstraint(
            "estado IN ('abierto','cerrado','bloqueado')",
            name="chk_estado_periodo"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(Date, nullable=False)
    fecha_cierre: Mapped[datetime] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="abierto", nullable=False)
    cerrado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)

    reaperturas: Mapped[list["CntPeriodoReapertura"]] = relationship(
        "CntPeriodoReapertura", back_populates="periodo"
    )


class CntPeriodoReapertura(Base):
    __tablename__ = "cnt_periodo_reapertura"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    periodo_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("cnt_periodo.id"), nullable=False
    )
    estado_anterior: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    autorizado_por: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    periodo: Mapped["CntPeriodo"] = relationship("CntPeriodo", back_populates="reaperturas")


# ---------------------------------------------------------------------------
# Plan de cuentas PUC
# ---------------------------------------------------------------------------

class CntCuenta(Base, AuditMixin):
    __tablename__ = "cnt_cuenta"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_cuenta_codigo"),
        CheckConstraint("nivel BETWEEN 1 AND 9", name="chk_cuenta_nivel"),
        CheckConstraint("naturaleza IN ('DEBITO','CREDITO')", name="chk_cuenta_naturaleza"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    nivel: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    naturaleza: Mapped[str] = mapped_column(String(10), nullable=False)   # DEBITO | CREDITO
    acepta_movimiento: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requiere_tercero: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requiere_cc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    padre_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    padre: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", remote_side="CntCuenta.id", back_populates="hijos")
    hijos: Mapped[list["CntCuenta"]] = relationship("CntCuenta", back_populates="padre")


# ---------------------------------------------------------------------------
# Centros de costo
# ---------------------------------------------------------------------------

class CntCentroCosto(Base, AuditMixin):
    __tablename__ = "cnt_centro_costo"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_centro_costo_codigo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    padre_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("cnt_centro_costo.id"), nullable=True
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    padre: Mapped[Optional["CntCentroCosto"]] = relationship("CntCentroCosto", remote_side="CntCentroCosto.id", back_populates="hijos")
    hijos: Mapped[list["CntCentroCosto"]] = relationship("CntCentroCosto", back_populates="padre")


# ---------------------------------------------------------------------------
# Asientos contables
# ---------------------------------------------------------------------------

_asiento_numero_seq = Sequence("cnt_asiento_numero_seq", start=1)


class CntAsiento(Base, AuditMixin):
    __tablename__ = "cnt_asiento"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_asiento_numero"),
        UniqueConstraint("documento_numero", name="uq_asiento_documento_numero"),
        CheckConstraint("estado IN ('borrador','publicado')", name="chk_asiento_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[int] = mapped_column(BigInteger, _asiento_numero_seq, server_default=_asiento_numero_seq.next_value(), nullable=False)
    documento_numero: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tipo_documento.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(Date, nullable=False)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_periodo.id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    documento_origen_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    documento_origen_tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)
    moneda_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_moneda.id"), nullable=False)
    trm: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    asiento_origen_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_asiento.id"), nullable=True)

    lineas: Mapped[list["CntAsientoLinea"]] = relationship("CntAsientoLinea", back_populates="asiento", cascade="all, delete-orphan")
    periodo: Mapped["CntPeriodo"] = relationship("CntPeriodo")
    moneda: Mapped["AdmMoneda"] = relationship("AdmMoneda", foreign_keys=[moneda_id])
    asiento_origen: Mapped[Optional["CntAsiento"]] = relationship("CntAsiento", remote_side="CntAsiento.id")


class CntAsientoLinea(Base):
    __tablename__ = "cnt_asiento_linea"
    __table_args__ = (
        CheckConstraint(
            "(debito > 0 AND credito = 0) OR (credito > 0 AND debito = 0)",
            name="chk_linea_debito_credito"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asiento_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_asiento.id", ondelete="CASCADE"), nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=False)
    debito: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    credito: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    debito_funcional: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    credito_funcional: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    tercero_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    centro_costo_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_centro_costo.id"), nullable=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    asiento: Mapped["CntAsiento"] = relationship("CntAsiento", back_populates="lineas")
    cuenta: Mapped["CntCuenta"] = relationship("CntCuenta")


class CntAsientoCorreccion(Base):
    __tablename__ = "cnt_asiento_correccion"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asiento_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_asiento.id", ondelete="CASCADE"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(pg.TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_lineas: Mapped[dict] = mapped_column(pg.JSONB, nullable=False)


