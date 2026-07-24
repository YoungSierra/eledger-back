from datetime import date, datetime
from typing import Optional
import uuid

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, func,
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


_ESTADOS_REQ = "('PENDIENTE','EN_PROCESO','REVISION','REALIZADO')"
_PRIORIDADES = "('BAJA','MEDIA','ALTA')"
_TIPOS_MSG = "('COMENTARIO','CAMBIO_ESTADO')"


class ReqRequerimiento(Base, AuditMixin):
    """Requerimiento interno: un usuario le solicita una acción a otro."""
    __tablename__ = "req_requerimiento"
    __table_args__ = (
        CheckConstraint(f"estado IN {_ESTADOS_REQ}", name="chk_req_estado"),
        CheckConstraint(f"prioridad IN {_PRIORIDADES}", name="chk_req_prioridad"),
        Index("idx_req_asignado", "asignado_id"),
        Index("idx_req_solicitante", "solicitante_id"),
        Index("idx_req_estado", "estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    asunto: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    solicitante_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=False)
    asignado_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", nullable=False)
    prioridad: Mapped[str] = mapped_column(String(10), default="MEDIA", nullable=False)
    fecha_limite: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Adjunto único del requerimiento principal (reemplazable en cualquier momento).
    archivo_nombre: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    archivo_ruta: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    solicitante: Mapped["AdmUsuario"] = relationship("AdmUsuario", foreign_keys=[solicitante_id])
    asignado: Mapped["AdmUsuario"] = relationship("AdmUsuario", foreign_keys=[asignado_id])
    mensajes: Mapped[list["ReqMensaje"]] = relationship(
        "ReqMensaje", back_populates="requerimiento", cascade="all, delete-orphan"
    )


class ReqMensaje(Base):
    """Traza del requerimiento: comentarios y cambios de estado en orden cronológico."""
    __tablename__ = "req_mensaje"
    __table_args__ = (
        CheckConstraint(f"tipo IN {_TIPOS_MSG}", name="chk_req_msg_tipo"),
        Index("idx_req_msg_requerimiento", "requerimiento_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requerimiento_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("req_requerimiento.id"), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="COMENTARIO", nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    estado_nuevo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    requerimiento: Mapped["ReqRequerimiento"] = relationship("ReqRequerimiento", back_populates="mensajes")
    usuario: Mapped["AdmUsuario"] = relationship("AdmUsuario", foreign_keys=[usuario_id])
