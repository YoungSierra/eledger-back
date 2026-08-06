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
    # `municipio_codigo` es la fuente de verdad (DIVIPOLA); ciudad/departamento se
    # mantienen sincronizados desde el catálogo. El código de 5 dígitos lo exige
    # la facturación electrónica para identificar al adquiriente.
    municipio_codigo: Mapped[Optional[str]] = mapped_column(String(5), ForeignKey("adm_municipio.codigo"), nullable=True)
    ciudad: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    departamento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pais: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # ISO 3166-1 alpha-2. Es lo que exige la DIAN; `pais` en texto queda como
    # respaldo de lo ya capturado. Si no es "CO", `municipio_codigo` va nulo y
    # la ciudad/estado del exterior viven en los campos de texto.
    pais_codigo: Mapped[Optional[str]] = mapped_column(String(2), ForeignKey("adm_pais.codigo"), nullable=True)
    # Catálogo DIAN de tipo de documento de identificación (13 CC, 31 NIT,
    # 50 NIT otro país, 42 doc. extranjero…). Antes se deducía de tipo_persona,
    # lo que solo producía 13 o 31 y era incorrecto para extranjeros.
    tipo_documento_dian: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nombre_contacto: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    cargo_contacto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telefono_contacto: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email_contacto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    asesor_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=True)

    asesor: Mapped[Optional["AdmUsuario"]] = relationship("AdmUsuario", foreign_keys=[asesor_id])
