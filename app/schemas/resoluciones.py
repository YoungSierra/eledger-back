from datetime import date
from typing import Optional
import uuid
from pydantic import BaseModel, Field, model_validator


class ResolucionCreate(BaseModel):
    tipo: str = Field("FACTURA_VENTA", pattern="^(FACTURA_VENTA|NOTA_CREDITO|NOTA_DEBITO)$")
    numero_resolucion: str = Field(..., max_length=50)
    prefijo: Optional[str] = Field(None, max_length=10)
    rango_desde: int = Field(..., ge=1)
    rango_hasta: int = Field(..., ge=1)
    fecha_desde: date
    fecha_hasta: date

    @model_validator(mode="after")
    def validar_rangos(self) -> "ResolucionCreate":
        if self.rango_hasta < self.rango_desde:
            raise ValueError("rango_hasta debe ser mayor o igual a rango_desde")
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("fecha_hasta debe ser posterior a fecha_desde")
        return self


class ResolucionUpdate(BaseModel):
    tipo: Optional[str] = Field(None, pattern="^(FACTURA_VENTA|NOTA_CREDITO|NOTA_DEBITO)$")
    numero_resolucion: Optional[str] = Field(None, max_length=50)
    prefijo: Optional[str] = Field(None, max_length=10)
    rango_desde: Optional[int] = Field(None, ge=1)
    rango_hasta: Optional[int] = Field(None, ge=1)
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    activo: Optional[bool] = None


class ResolucionResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    numero_resolucion: str
    prefijo: Optional[str]
    rango_desde: int
    rango_hasta: int
    consecutivo_actual: int
    fecha_desde: date
    fecha_hasta: date
    activo: bool
    disponibles: int = 0
    vencida: bool = False

    model_config = {"from_attributes": True}
