from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel


class DevolucionLineaCreate(BaseModel):
    factura_linea_id: uuid.UUID
    cantidad: Decimal  # cantidad a devolver (<= cantidad facturada pendiente de devolver)


class DevolucionCreate(BaseModel):
    factura_id: uuid.UUID
    fecha: date
    motivo: str
    concepto_dian: Optional[str] = None
    descripcion: Optional[str] = None
    lineas: list[DevolucionLineaCreate]


class DevolucionUpdate(BaseModel):
    fecha: Optional[date] = None
    motivo: Optional[str] = None
    concepto_dian: Optional[str] = None
    descripcion: Optional[str] = None
    lineas: Optional[list[DevolucionLineaCreate]] = None


class AnularDevolucionRequest(BaseModel):
    motivo: str


class DevolucionLineaResponse(BaseModel):
    id: uuid.UUID
    orden: int
    factura_linea_id: uuid.UUID
    producto_id: Optional[uuid.UUID] = None
    producto_codigo: Optional[str] = None
    producto_nombre: Optional[str] = None
    descripcion: str
    cantidad: Decimal
    cantidad_facturada: Optional[Decimal] = None
    precio_unitario: Decimal
    subtotal: Decimal
    iva_tipo: str
    iva_pct: Decimal
    total_iva: Decimal
    total: Decimal
    cuenta_devolucion_id: Optional[uuid.UUID] = None
    cuenta_devolucion_codigo: Optional[str] = None
    cuenta_devolucion_nombre: Optional[str] = None
    cuenta_iva_id: Optional[uuid.UUID] = None
    centro_costo_id: Optional[uuid.UUID] = None
    es_producto: bool = False

    model_config = {"from_attributes": True}


class DevolucionResponse(BaseModel):
    id: uuid.UUID
    numero: str
    factura_id: uuid.UUID
    factura_numero: Optional[str] = None
    fecha: date
    motivo: str
    concepto_dian: Optional[str] = None
    periodo_id: uuid.UUID
    cliente_id: uuid.UUID
    cliente_nit: Optional[str] = None
    cliente_nombre: Optional[str] = None
    moneda_id: uuid.UUID
    moneda_codigo: str
    trm: Optional[Decimal] = None
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    descripcion: Optional[str] = None
    estado: str
    asiento_id: Optional[uuid.UUID] = None
    cxc_documento_id: Optional[uuid.UUID] = None
    cune: Optional[str] = None
    dian_estado: Optional[str] = None
    lineas: list[DevolucionLineaResponse] = []
    creado_en: datetime
    creado_por: uuid.UUID

    model_config = {"from_attributes": True}


class DevolucionListItem(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    factura_id: uuid.UUID
    factura_numero: Optional[str] = None
    cliente_nombre: Optional[str] = None
    moneda_codigo: str
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    estado: str
    dian_estado: Optional[str] = None
    creado_en: datetime

    model_config = {"from_attributes": True}


class DevolucionListResponse(BaseModel):
    items: list[DevolucionListItem]
    total: int
    pagina: int
    por_pagina: int


# --- Preview del asiento (mismo shape que facturación) ---

class DevPreviewLinea(BaseModel):
    cuenta_codigo: Optional[str] = None
    cuenta_nombre: Optional[str] = None
    tercero_nombre: Optional[str] = None
    centro_costo: Optional[str] = None
    debito: Decimal = Decimal("0")
    credito: Decimal = Decimal("0")


class DevPreviewResponse(BaseModel):
    lineas: list[DevPreviewLinea]
    total_debito: Decimal
    total_credito: Decimal
    cuadra: bool
    moneda_codigo: Optional[str] = None
    avisos: list[str] = []
    asiento_numero: Optional[int] = None
