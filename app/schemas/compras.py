from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel


# ─── OC ──────────────────────────────────────────────────────────────────────

class OcLineaCreate(BaseModel):
    producto_id: uuid.UUID
    cantidad: Decimal
    um_id: uuid.UUID
    precio_unitario: Decimal
    descuento_pct: Decimal = Decimal("0")
    iva_pct: Decimal = Decimal("0")
    tarifa_iva_id: Optional[uuid.UUID] = None
    centro_costo_id: Optional[uuid.UUID] = None


class OcCreate(BaseModel):
    fecha: date
    fecha_entrega_esperada: Optional[date] = None
    proveedor_id: uuid.UUID
    moneda_id: uuid.UUID
    trm: Optional[Decimal] = None
    notas: Optional[str] = None
    lineas: list[OcLineaCreate]


class OcUpdate(BaseModel):
    fecha: Optional[date] = None
    fecha_entrega_esperada: Optional[date] = None
    proveedor_id: Optional[uuid.UUID] = None
    moneda_id: Optional[uuid.UUID] = None
    trm: Optional[Decimal] = None
    notas: Optional[str] = None
    lineas: Optional[list[OcLineaCreate]] = None


class OcLineaResponse(BaseModel):
    id: uuid.UUID
    producto_id: uuid.UUID
    producto_codigo: Optional[str]
    producto_nombre: Optional[str]
    maneja_inventario: bool
    cantidad: Decimal
    um_id: uuid.UUID
    um_codigo: Optional[str]
    cantidad_base: Decimal
    precio_unitario: Decimal
    descuento_pct: Decimal
    subtotal: Decimal
    iva_pct: Decimal
    total_iva: Decimal
    total: Decimal
    tarifa_iva_id: Optional[uuid.UUID]
    centro_costo_id: Optional[uuid.UUID]
    centro_costo_codigo: Optional[str]
    centro_costo_nombre: Optional[str]
    cantidad_recibida: Decimal
    pendiente: Decimal


class OcResponse(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    fecha_entrega_esperada: Optional[date]
    periodo_id: uuid.UUID
    proveedor_id: uuid.UUID
    proveedor_nit: Optional[str]
    proveedor_nombre: Optional[str]
    moneda_id: uuid.UUID
    moneda_codigo: Optional[str]
    trm: Optional[Decimal]
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    notas: Optional[str]
    estado: str
    creado_por: uuid.UUID
    aprobado_por: Optional[uuid.UUID]
    aprobado_en: Optional[datetime]
    lineas: list[OcLineaResponse]


class OcListItem(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    proveedor_nit: Optional[str]
    proveedor_nombre: Optional[str]
    moneda_codigo: Optional[str]
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    estado: str
    recepciones_count: int


class OcListResponse(BaseModel):
    items: list[OcListItem]
    total: int
    pagina: int
    por_pagina: int


# ─── Recepción ───────────────────────────────────────────────────────────────

class RecepcionLineaCreate(BaseModel):
    oc_linea_id: uuid.UUID
    cantidad: Decimal
    costo_unitario: Decimal


class RecepcionCreate(BaseModel):
    fecha: date
    oc_id: uuid.UUID
    bodega_id: uuid.UUID
    notas: Optional[str] = None
    lineas: list[RecepcionLineaCreate]


class RecepcionUpdate(BaseModel):
    fecha: Optional[date] = None
    bodega_id: Optional[uuid.UUID] = None
    notas: Optional[str] = None
    lineas: Optional[list[RecepcionLineaCreate]] = None


class RecepcionLineaResponse(BaseModel):
    id: uuid.UUID
    oc_linea_id: uuid.UUID
    producto_id: uuid.UUID
    producto_codigo: Optional[str]
    producto_nombre: Optional[str]
    maneja_inventario: bool
    cantidad: Decimal
    um_id: uuid.UUID
    um_codigo: Optional[str]
    cantidad_base: Decimal
    costo_unitario: Decimal
    costo_total: Decimal


class RecepcionResponse(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    periodo_id: uuid.UUID
    oc_id: uuid.UUID
    oc_numero: Optional[str]
    bodega_id: uuid.UUID
    bodega_nombre: Optional[str]
    proveedor_id: uuid.UUID
    proveedor_nit: Optional[str]
    proveedor_nombre: Optional[str]
    notas: Optional[str]
    estado: str
    movimiento_id: Optional[uuid.UUID]
    asiento_id: Optional[uuid.UUID]
    total_costo: Decimal
    lineas: list[RecepcionLineaResponse]


class RecepcionListItem(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    oc_numero: Optional[str]
    bodega_nombre: Optional[str]
    proveedor_nit: Optional[str]
    proveedor_nombre: Optional[str]
    total_costo: Decimal
    estado: str


class RecepcionListResponse(BaseModel):
    items: list[RecepcionListItem]
    total: int
    pagina: int
    por_pagina: int
