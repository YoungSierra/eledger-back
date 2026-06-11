import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Líneas
# ---------------------------------------------------------------------------

class LineaCreate(BaseModel):
    cuenta_id: uuid.UUID
    debito: Decimal = Decimal("0")
    credito: Decimal = Decimal("0")
    tercero_id: Optional[uuid.UUID] = None
    centro_costo_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = None

    @model_validator(mode="after")
    def validar_debito_credito(self) -> "LineaCreate":
        d, c = self.debito, self.credito
        if not ((d > 0 and c == 0) or (c > 0 and d == 0)):
            raise ValueError("La línea debe tener débito o crédito, no ambos ni cero")
        return self


class LineaUpdate(BaseModel):
    cuenta_id: Optional[uuid.UUID] = None
    debito: Optional[Decimal] = None
    credito: Optional[Decimal] = None
    tercero_id: Optional[uuid.UUID] = None
    centro_costo_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = None

    @model_validator(mode="after")
    def validar_debito_credito(self) -> "LineaUpdate":
        d, c = self.debito, self.credito
        if d is not None or c is not None:
            d = d or Decimal("0")
            c = c or Decimal("0")
            if not ((d > 0 and c == 0) or (c > 0 and d == 0)):
                raise ValueError("La línea debe tener débito o crédito, no ambos ni cero")
        return self


class LineaResponse(BaseModel):
    id: uuid.UUID
    asiento_id: uuid.UUID
    orden: int
    cuenta_id: uuid.UUID
    cuenta_codigo: str
    cuenta_nombre: str
    debito: Decimal
    credito: Decimal
    debito_funcional: Decimal
    credito_funcional: Decimal
    tercero_id: Optional[uuid.UUID] = None
    tercero_nit: Optional[str] = None
    tercero_nombre: Optional[str] = None
    centro_costo_id: Optional[uuid.UUID] = None
    centro_costo_nombre: Optional[str] = None
    descripcion: Optional[str] = None
    requiere_tercero: bool = False
    requiere_cc: bool = False

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Asiento
# ---------------------------------------------------------------------------

class AsientoCreate(BaseModel):
    tipo_documento_id: uuid.UUID
    fecha: date
    descripcion: str
    moneda_id: uuid.UUID
    trm: Optional[Decimal] = None
    lineas: list[LineaCreate] = []

    @field_validator("descripcion")
    @classmethod
    def descripcion_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La descripción no puede estar vacía")
        return v.strip()


class AsientoUpdate(BaseModel):
    fecha: Optional[date] = None
    descripcion: Optional[str] = None
    moneda_id: Optional[uuid.UUID] = None
    trm: Optional[Decimal] = None

    @field_validator("descripcion")
    @classmethod
    def descripcion_no_vacia(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("La descripción no puede estar vacía")
        return v.strip() if v else v


class AsientoCorregirRequest(BaseModel):
    motivo: str
    descripcion: Optional[str] = None
    lineas: list[LineaCreate] = []

    @field_validator("motivo")
    @classmethod
    def motivo_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El motivo de corrección es obligatorio")
        return v.strip()


class AsientoResponse(BaseModel):
    id: uuid.UUID
    numero: int
    documento_numero: Optional[str] = None
    tipo_documento_id: uuid.UUID
    tipo_documento_codigo: str
    tipo_documento_nombre: str
    fecha: date
    periodo_id: uuid.UUID
    descripcion: str
    documento_origen_id: Optional[uuid.UUID] = None
    documento_origen_tipo: Optional[str] = None
    estado: Literal["borrador", "publicado"]
    moneda_id: uuid.UUID
    moneda_codigo: str
    trm: Optional[Decimal] = None
    asiento_origen_id: Optional[uuid.UUID] = None
    total_debito: Decimal
    total_credito: Decimal
    lineas: list[LineaResponse] = []
    creado_en: datetime
    creado_por: uuid.UUID

    model_config = {"from_attributes": True}


class AsientoListItem(BaseModel):
    id: uuid.UUID
    numero: int
    documento_numero: Optional[str] = None
    tipo_documento_codigo: str
    tipo_documento_nombre: str
    fecha: date
    descripcion: str
    estado: Literal["borrador", "publicado"]
    moneda_codigo: str
    total_debito: Decimal
    total_credito: Decimal
    documento_origen_id: Optional[uuid.UUID] = None
    creado_en: datetime

    model_config = {"from_attributes": True}


class AsientoListResponse(BaseModel):
    items: list[AsientoListItem]
    total: int
    pagina: int
    por_pagina: int
