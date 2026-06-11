from decimal import Decimal
from typing import Any, Optional
import uuid
from pydantic import BaseModel, Field

FORMATOS_EXTRACTO = ("OFX", "CSV", "EXCEL")


class BancoCreate(BaseModel):
    nombre: str = Field(..., max_length=150)
    codigo: Optional[str] = Field(None, max_length=20)
    nit: Optional[str] = Field(None, max_length=20)
    formato: Optional[str] = Field(None, pattern="^(OFX|CSV|EXCEL)$")
    mapeo_columnas: Optional[Any] = None
    fila_inicio: Optional[int] = Field(None, ge=1)
    formato_fecha: Optional[str] = Field(None, max_length=20)


class BancoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=150)
    codigo: Optional[str] = Field(None, max_length=20)
    nit: Optional[str] = Field(None, max_length=20)
    formato: Optional[str] = Field(None, pattern="^(OFX|CSV|EXCEL)$")
    mapeo_columnas: Optional[Any] = None
    fila_inicio: Optional[int] = Field(None, ge=1)
    formato_fecha: Optional[str] = Field(None, max_length=20)
    activo: Optional[bool] = None


class BancoResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    codigo: Optional[str]
    nit: Optional[str]
    formato: Optional[str]
    mapeo_columnas: Optional[Any]
    fila_inicio: Optional[int]
    formato_fecha: Optional[str]
    activo: bool
    model_config = {"from_attributes": True}


class CuentaBancariaCreate(BaseModel):
    banco_id: uuid.UUID
    nombre: str = Field(..., max_length=150)
    numero: str = Field(..., max_length=50)
    tipo: str = Field(..., pattern="^(CORRIENTE|AHORRO)$")
    moneda_id: Optional[uuid.UUID] = None
    cuenta_contable_id: Optional[uuid.UUID] = None
    saldo_inicial: Decimal = Field(Decimal("0"), ge=0)


class CuentaBancariaUpdate(BaseModel):
    banco_id: Optional[uuid.UUID] = None
    nombre: Optional[str] = Field(None, max_length=150)
    numero: Optional[str] = Field(None, max_length=50)
    tipo: Optional[str] = Field(None, pattern="^(CORRIENTE|AHORRO)$")
    moneda_id: Optional[uuid.UUID] = None
    cuenta_contable_id: Optional[uuid.UUID] = None
    saldo_inicial: Optional[Decimal] = Field(None, ge=0)
    activo: Optional[bool] = None


class CuentaBancariaResponse(BaseModel):
    id: uuid.UUID
    banco_id: uuid.UUID
    banco_nombre: Optional[str] = None
    nombre: str
    numero: str
    tipo: str
    moneda_id: Optional[uuid.UUID]
    moneda_codigo: Optional[str] = None
    cuenta_contable_id: Optional[uuid.UUID]
    cuenta_contable_codigo: Optional[str] = None
    cuenta_contable_nombre: Optional[str] = None
    saldo_inicial: Decimal
    activo: bool
    model_config = {"from_attributes": True}


class ChequerapCreate(BaseModel):
    cuenta_id: uuid.UUID
    prefijo: Optional[str] = Field(None, max_length=10)
    numero_desde: int = Field(..., ge=1)
    numero_hasta: int = Field(..., ge=1)
    descripcion: Optional[str] = Field(None, max_length=255)


class ChequeraUpdate(BaseModel):
    prefijo: Optional[str] = Field(None, max_length=10)
    numero_desde: Optional[int] = Field(None, ge=1)
    numero_hasta: Optional[int] = Field(None, ge=1)
    estado: Optional[str] = Field(None, pattern="^(ACTIVA|AGOTADA|ANULADA)$")
    descripcion: Optional[str] = Field(None, max_length=255)
    activo: Optional[bool] = None


class ChequeraResponse(BaseModel):
    id: uuid.UUID
    cuenta_id: uuid.UUID
    cuenta_nombre: Optional[str] = None
    banco_nombre: Optional[str] = None
    prefijo: Optional[str]
    numero_desde: int
    numero_hasta: int
    consecutivo_actual: int
    estado: str
    descripcion: Optional[str]
    activo: bool
    model_config = {"from_attributes": True}
