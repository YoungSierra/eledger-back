from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Numeric, SmallInteger,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


class NomPeriodo(Base, AuditMixin):
    """Documento de nómina electrónica de un período de pago (solo transmisión,
    _eLedger no liquida nómina). Reúne el detalle por empleado y su estado ante DIAN."""
    __tablename__ = "nom_periodo"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_nom_periodo_numero"),
        CheckConstraint("tipo IN ('NOMINA','AJUSTE')", name="chk_nom_periodo_tipo"),
        CheckConstraint(
            "estado IN ('borrador','generado','enviado','aceptado','rechazado','anulado')",
            name="chk_nom_periodo_estado",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="NOMINA", nullable=False)
    periodo_pago_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_pago_fin: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_generacion: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_periodo.id"), nullable=False)
    total_devengado: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_deducciones: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_neto: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)
    # DIAN (para transmitir después vía PTH)
    cune: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dian_estado: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    dian_mensaje: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    xml_key: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)  # storage key del XML (R2)

    empleados: Mapped[list["NomEmpleado"]] = relationship(
        "NomEmpleado", back_populates="periodo", cascade="all, delete-orphan",
        order_by="NomEmpleado.orden",
    )
    eventos: Mapped[list["NomEvento"]] = relationship(
        "NomEvento", back_populates="periodo", cascade="all, delete-orphan",
        order_by="NomEvento.creado_en",
    )


class NomEmpleado(Base):
    """Detalle de pago de un empleado dentro de un período. Datos de identificación
    en línea (el módulo no requiere maestro de empleados para transmitir)."""
    __tablename__ = "nom_empleado"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("nom_periodo.id", ondelete="CASCADE"), nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    # Identificación
    tipo_documento: Mapped[str] = mapped_column(String(10), default="CC", nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(30), nullable=False)
    primer_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    otros_nombres: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    primer_apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    segundo_apellido: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cargo: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    # Base
    salario_basico: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    dias_trabajados: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    # Devengados comunes
    sueldo: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    auxilio_transporte: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    horas_extra: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    bonificaciones: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    comisiones: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    devengados_extra: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)  # {concepto: valor}
    # Deducciones comunes
    salud: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    pension: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    fondo_solidaridad: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    retencion_fuente: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    deducciones_extra: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)
    # Totales
    total_devengado: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_deducciones: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    neto: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)

    periodo: Mapped["NomPeriodo"] = relationship("NomPeriodo", back_populates="empleados")


class NomEvento(Base):
    """Bitácora de transmisión a DIAN/PTH."""
    __tablename__ = "nom_evento"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    periodo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("nom_periodo.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # ENVIO | RESPUESTA | ERROR | REINTENTO
    estado: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mensaje: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    respuesta: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)

    periodo: Mapped["NomPeriodo"] = relationship("NomPeriodo", back_populates="eventos")
