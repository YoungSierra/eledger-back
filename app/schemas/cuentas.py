import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


NivelType = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
NaturalezaType = Literal["DEBITO", "CREDITO"]


class CuentaCreate(BaseModel):
    codigo: str
    nombre: str
    naturaleza: NaturalezaType
    padre_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = None
    requiere_tercero: bool = False
    requiere_cc: bool = False

    @field_validator("codigo")
    @classmethod
    def codigo_valido(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("El código solo puede contener dígitos")
        if len(v) < 1 or len(v) > 20:
            raise ValueError("El código debe tener entre 1 y 20 dígitos")
        return v


class CuentaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    acepta_movimiento: Optional[bool] = None
    requiere_tercero: Optional[bool] = None
    requiere_cc: Optional[bool] = None


class CuentaResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    nivel: int
    naturaleza: NaturalezaType
    acepta_movimiento: bool
    requiere_tercero: bool
    requiere_cc: bool
    padre_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = None
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}
