from datetime import datetime
import uuid

from sqlalchemy import Boolean, BigInteger, DateTime, String, func
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AdmAdjunto(Base):
    """Adjunto genérico: se asocia a cualquier documento por (entidad, entidad_id)."""
    __tablename__ = "adm_adjunto"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entidad: Mapped[str] = mapped_column(String(50), nullable=False)          # p.ej. 'cxp_documento'
    entidad_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    tamano: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subido_por: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)
    subido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
