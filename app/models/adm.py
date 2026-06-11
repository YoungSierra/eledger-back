from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.admin import AdmUsuario

from app.core.database import Base
from app.models.base import AuditMixin


class AdmTercero(Base, AuditMixin):
    __tablename__ = "adm_tercero"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nit: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    digito_verif: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nombre1: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nombre2: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    apellido1: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    apellido2: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tipo_persona: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo_tercero: Mapped[str] = mapped_column(String(50), nullable=False)
    regimen: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    responsable_iva: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ciudad: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    departamento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pais: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nombre_contacto: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    cargo_contacto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telefono_contacto: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email_contacto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    asesor_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=True)

    asesor: Mapped[Optional["AdmUsuario"]] = relationship("AdmUsuario", foreign_keys=[asesor_id])
