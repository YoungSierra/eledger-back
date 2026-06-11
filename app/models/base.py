from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    """Columnas de auditoría presentes en todas las tablas."""

    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    creado_por: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), nullable=False
    )
    modificado_en: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    modificado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True), nullable=True
    )
