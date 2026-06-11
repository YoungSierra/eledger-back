"""Schemas para maestros financieros: monedas, condiciones de pago, tarifas IVA, retenciones."""
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Moneda
# ---------------------------------------------------------------------------

class MonedaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=3)
    nombre: str = Field(..., max_length=100)
    simbolo: str = Field(..., max_length=10)
    decimales: int = Field(2, ge=0, le=6)
    es_funcional: bool = False


class MonedaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    simbolo: Optional[str] = Field(None, max_length=10)
    decimales: Optional[int] = Field(None, ge=0, le=6)
    es_funcional: Optional[bool] = None
    activo: Optional[bool] = None


class MonedaResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    simbolo: str
    decimales: int
    es_funcional: bool
    activo: bool
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Condición de pago
# ---------------------------------------------------------------------------

class CondicionPagoCreate(BaseModel):
    codigo: str = Field(..., max_length=20)
    nombre: str = Field(..., max_length=100)
    dias_vencimiento: int = Field(0, ge=0)
    descuento_pct: Decimal = Field(Decimal("0"), ge=0, le=100)


class CondicionPagoUpdate(BaseModel):
    codigo: Optional[str] = Field(None, max_length=20)
    nombre: Optional[str] = Field(None, max_length=100)
    dias_vencimiento: Optional[int] = Field(None, ge=0)
    descuento_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    activo: Optional[bool] = None


class CondicionPagoResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    dias_vencimiento: int
    descuento_pct: Decimal
    activo: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Tarifa IVA
# ---------------------------------------------------------------------------

class TarifaIvaCreate(BaseModel):
    nombre: str = Field(..., max_length=100)
    tipo: str = Field(..., pattern="^(GRAVADO|EXENTO|EXCLUIDO)$")
    porcentaje: Decimal = Field(Decimal("0"), ge=0, le=100)
    cuenta_iva_ventas_id: Optional[uuid.UUID] = None
    cuenta_iva_compras_id: Optional[uuid.UUID] = None


class TarifaIvaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    tipo: Optional[str] = Field(None, pattern="^(GRAVADO|EXENTO|EXCLUIDO)$")
    porcentaje: Optional[Decimal] = Field(None, ge=0, le=100)
    cuenta_iva_ventas_id: Optional[uuid.UUID] = None
    cuenta_iva_compras_id: Optional[uuid.UUID] = None
    activo: Optional[bool] = None


class TarifaIvaResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    tipo: str
    porcentaje: Decimal
    cuenta_iva_ventas_id: Optional[uuid.UUID]
    cuenta_iva_ventas_codigo: Optional[str] = None
    cuenta_iva_ventas_nombre: Optional[str] = None
    cuenta_iva_compras_id: Optional[uuid.UUID]
    cuenta_iva_compras_codigo: Optional[str] = None
    cuenta_iva_compras_nombre: Optional[str] = None
    activo: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Retención
# ---------------------------------------------------------------------------

class RetencionCreate(BaseModel):
    tipo: str = Field(..., pattern="^(RETEFUENTE|RETEICA|RETEIVA)$")
    nombre: str = Field(..., max_length=150)
    porcentaje: Decimal = Field(..., ge=0, le=100)
    base_minima: Optional[Decimal] = None
    cuenta_compras_id: Optional[uuid.UUID] = None
    cuenta_ventas_id: Optional[uuid.UUID] = None
    aplica_compra: bool = True
    aplica_venta: bool = True


class RetencionUpdate(BaseModel):
    tipo: Optional[str] = Field(None, pattern="^(RETEFUENTE|RETEICA|RETEIVA)$")
    nombre: Optional[str] = Field(None, max_length=150)
    porcentaje: Optional[Decimal] = Field(None, ge=0, le=100)
    base_minima: Optional[Decimal] = None
    cuenta_compras_id: Optional[uuid.UUID] = None
    cuenta_ventas_id: Optional[uuid.UUID] = None
    aplica_compra: Optional[bool] = None
    aplica_venta: Optional[bool] = None
    activo: Optional[bool] = None


class RetencionResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    nombre: str
    porcentaje: Decimal
    base_minima: Optional[Decimal]
    cuenta_compras_id: Optional[uuid.UUID]
    cuenta_compras_codigo: Optional[str] = None
    cuenta_compras_nombre: Optional[str] = None
    cuenta_ventas_id: Optional[uuid.UUID]
    cuenta_ventas_codigo: Optional[str] = None
    cuenta_ventas_nombre: Optional[str] = None
    aplica_compra: bool
    aplica_venta: bool
    activo: bool

    model_config = {"from_attributes": True}
