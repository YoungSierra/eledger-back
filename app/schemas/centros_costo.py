import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CentroCostoCreate(BaseModel):
    codigo: str
    nombre: str
    padre_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = None


class CentroCostoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None


class CentroCostoResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    padre_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = None
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}
