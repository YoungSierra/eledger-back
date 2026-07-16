import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


class PeriodoCreate(BaseModel):
    anio: int
    mes: int
    fecha_inicio: date
    fecha_cierre: date

    @field_validator("mes")
    @classmethod
    def mes_valido(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("El mes debe estar entre 1 y 12")
        return v

    @model_validator(mode="after")
    def fechas_validas(self) -> "PeriodoCreate":
        if self.fecha_cierre < self.fecha_inicio:
            raise ValueError("fecha_cierre debe ser igual o posterior a fecha_inicio")
        return self


class GenerarAnioRequest(BaseModel):
    anio: int

    @field_validator("anio")
    @classmethod
    def anio_valido(cls, v: int) -> int:
        if not 2000 <= v <= 2100:
            raise ValueError("Año fuera de rango")
        return v


class PeriodoUpdate(BaseModel):
    fecha_inicio: date
    fecha_cierre: date

    @model_validator(mode="after")
    def fechas_validas(self) -> "PeriodoUpdate":
        if self.fecha_cierre < self.fecha_inicio:
            raise ValueError("fecha_cierre debe ser igual o posterior a fecha_inicio")
        return self


class PeriodoResponse(BaseModel):
    id: uuid.UUID
    anio: int
    mes: int
    fecha_inicio: date
    fecha_cierre: date
    estado: Literal["abierto", "cerrado", "bloqueado"]
    cerrado_en: Optional[datetime] = None
    cerrado_por: Optional[uuid.UUID] = None
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}
