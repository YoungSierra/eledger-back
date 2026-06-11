from decimal import Decimal
from typing import Optional
import uuid
from pydantic import BaseModel, Field


class ConceptoRetencionIn(BaseModel):
    retencion_id: uuid.UUID


class ConceptoRetencionOut(BaseModel):
    id: uuid.UUID
    retencion_id: uuid.UUID
    retencion_nombre: Optional[str] = None
    retencion_tipo: Optional[str] = None
    retencion_porcentaje: Optional[Decimal] = None
    retencion_cuenta_compras_id: Optional[uuid.UUID] = None
    retencion_cuenta_compras_codigo: Optional[str] = None
    activo: bool
    model_config = {"from_attributes": True}


class ConceptoCreate(BaseModel):
    codigo: str = Field(..., max_length=50)
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    tarifa_iva_id: Optional[uuid.UUID] = None
    cuenta_gasto_id: Optional[uuid.UUID] = None
    cuenta_cxp_id: Optional[uuid.UUID] = None
    retenciones: list[ConceptoRetencionIn] = []


class ConceptoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=200)
    descripcion: Optional[str] = None
    tarifa_iva_id: Optional[uuid.UUID] = None
    cuenta_gasto_id: Optional[uuid.UUID] = None
    cuenta_cxp_id: Optional[uuid.UUID] = None
    retenciones: Optional[list[ConceptoRetencionIn]] = None
    activo: Optional[bool] = None


class ConceptoResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    modulo: str
    descripcion: Optional[str]
    tarifa_iva_id: Optional[uuid.UUID]
    tarifa_iva_nombre: Optional[str] = None
    tarifa_iva_tipo: Optional[str] = None
    tarifa_iva_porcentaje: Optional[Decimal] = None
    tarifa_iva_cuenta_compras_id: Optional[uuid.UUID] = None
    tarifa_iva_cuenta_compras_codigo: Optional[str] = None
    cuenta_gasto_id: Optional[uuid.UUID]
    cuenta_gasto_codigo: Optional[str] = None
    cuenta_gasto_nombre: Optional[str] = None
    cuenta_cxp_id: Optional[uuid.UUID]
    cuenta_cxp_codigo: Optional[str] = None
    cuenta_cxp_nombre: Optional[str] = None
    activo: bool
    retenciones: list[ConceptoRetencionOut] = []
    model_config = {"from_attributes": True}
