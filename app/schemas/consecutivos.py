from typing import Optional
import uuid
from pydantic import BaseModel, Field


class ConsecutivoCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=100)
    prefijo: Optional[str] = Field(None, max_length=20)
    numero_inicio: int = Field(1, ge=1)
    longitud_minima: int = Field(5, ge=1, le=20)


class ConsecutivoUpdate(BaseModel):
    prefijo: Optional[str] = Field(None, max_length=20)
    numero_inicio: Optional[int] = Field(None, ge=1)
    longitud_minima: Optional[int] = Field(None, ge=1, le=20)
    activo: Optional[bool] = None


class ConsecutivoResponse(BaseModel):
    es_personalizado: bool = False  # True si lo creó el usuario (se puede eliminar)
    id: uuid.UUID
    tipo_documento_id: uuid.UUID
    tipo_documento_codigo: str
    tipo_documento_nombre: str
    tipo_documento_modulo: str
    prefijo: Optional[str]
    numero_actual: int
    numero_inicio: int
    longitud_minima: int
    ejemplo: str  # muestra cómo quedaría el próximo número
    activo: bool
