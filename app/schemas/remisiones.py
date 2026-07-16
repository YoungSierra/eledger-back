from datetime import date
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class RemisionLineaCreate(BaseModel):
    producto_id: uuid.UUID
    cantidad: Decimal = Field(gt=0)
    um_id: uuid.UUID


class RemisionCreate(BaseModel):
    fecha: date
    cliente_id: uuid.UUID
    bodega_id: uuid.UUID
    cotizacion_id: Optional[uuid.UUID] = None
    notas: Optional[str] = None
    lineas: list[RemisionLineaCreate] = Field(min_length=1)


class RemisionLinea(BaseModel):
    id: uuid.UUID
    producto_id: uuid.UUID
    producto_codigo: str
    producto_nombre: str
    cantidad: Decimal
    um_id: uuid.UUID
    um_codigo: str
    costo_unitario: Decimal


class RemisionDetalle(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: str
    cliente_id: uuid.UUID
    cliente_nombre: str
    cliente_nit: Optional[str] = None
    bodega_id: uuid.UUID
    bodega_nombre: str
    notas: Optional[str]
    estado: str
    movimiento_id: Optional[uuid.UUID]
    asiento_id: Optional[uuid.UUID]
    lineas: list[RemisionLinea]


class RemisionListItem(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: str
    cliente_id: uuid.UUID
    cliente_nombre: str
    cliente_nit: str | None = None
    bodega_id: uuid.UUID
    bodega_nombre: str
    estado: str
    num_lineas: int


class RemisionListResponse(BaseModel):
    items: list[RemisionListItem]
    total: int
    pagina: int
    por_pagina: int
