from datetime import date
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Familia
# ---------------------------------------------------------------------------

class FamiliaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = None
    cuenta_inventario_id: Optional[uuid.UUID] = None
    cuenta_costo_ventas_id: Optional[uuid.UUID] = None
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    cuenta_devolucion_venta_id: Optional[uuid.UUID] = None
    cuenta_devolucion_compra_id: Optional[uuid.UUID] = None
    cuenta_ajuste_entrada_id: Optional[uuid.UUID] = None
    cuenta_ajuste_salida_id: Optional[uuid.UUID] = None


class FamiliaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = None
    cuenta_inventario_id: Optional[uuid.UUID] = None
    cuenta_costo_ventas_id: Optional[uuid.UUID] = None
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    cuenta_devolucion_venta_id: Optional[uuid.UUID] = None
    cuenta_devolucion_compra_id: Optional[uuid.UUID] = None
    cuenta_ajuste_entrada_id: Optional[uuid.UUID] = None
    cuenta_ajuste_salida_id: Optional[uuid.UUID] = None
    activo: Optional[bool] = None


class FamiliaResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: Optional[str]
    cuenta_inventario_id: Optional[uuid.UUID]
    cuenta_inventario_display: Optional[str]
    cuenta_costo_ventas_id: Optional[uuid.UUID]
    cuenta_costo_ventas_display: Optional[str]
    cuenta_ingreso_id: Optional[uuid.UUID]
    cuenta_ingreso_display: Optional[str]
    cuenta_devolucion_venta_id: Optional[uuid.UUID]
    cuenta_devolucion_venta_display: Optional[str]
    cuenta_devolucion_compra_id: Optional[uuid.UUID]
    cuenta_devolucion_compra_display: Optional[str]
    cuenta_ajuste_entrada_id: Optional[uuid.UUID]
    cuenta_ajuste_entrada_display: Optional[str]
    cuenta_ajuste_salida_id: Optional[uuid.UUID]
    cuenta_ajuste_salida_display: Optional[str]
    activo: bool


# ---------------------------------------------------------------------------
# Unidad de medida
# ---------------------------------------------------------------------------

class UnidadMedidaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=100)


class UnidadMedidaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    activo: Optional[bool] = None


class UnidadMedidaResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    activo: bool
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Tipo de producto
# ---------------------------------------------------------------------------

class TipoProductoUpdate(BaseModel):
    cuenta_inventario_id: Optional[uuid.UUID] = None
    cuenta_costo_ventas_id: Optional[uuid.UUID] = None
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    cuenta_devolucion_venta_id: Optional[uuid.UUID] = None
    cuenta_devolucion_compra_id: Optional[uuid.UUID] = None
    cuenta_ajuste_entrada_id: Optional[uuid.UUID] = None
    cuenta_ajuste_salida_id: Optional[uuid.UUID] = None


class TipoProductoResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    maneja_inventario: bool
    cuenta_inventario_id: Optional[uuid.UUID]
    cuenta_inventario_display: Optional[str]
    cuenta_costo_ventas_id: Optional[uuid.UUID]
    cuenta_costo_ventas_display: Optional[str]
    cuenta_ingreso_id: Optional[uuid.UUID]
    cuenta_ingreso_display: Optional[str]
    cuenta_devolucion_venta_id: Optional[uuid.UUID]
    cuenta_devolucion_venta_display: Optional[str]
    cuenta_devolucion_compra_id: Optional[uuid.UUID]
    cuenta_devolucion_compra_display: Optional[str]
    cuenta_ajuste_entrada_id: Optional[uuid.UUID]
    cuenta_ajuste_entrada_display: Optional[str]
    cuenta_ajuste_salida_id: Optional[uuid.UUID]
    cuenta_ajuste_salida_display: Optional[str]


# ---------------------------------------------------------------------------
# Producto
# ---------------------------------------------------------------------------

class ProductoCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    tipo_id: uuid.UUID
    familia_id: Optional[uuid.UUID] = None
    um_base_id: uuid.UUID
    maneja_inventario: bool = True
    maneja_series: bool = False
    maneja_lotes: bool = False
    cuenta_inventario_id: Optional[uuid.UUID] = None
    cuenta_costo_ventas_id: Optional[uuid.UUID] = None
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    cuenta_devolucion_venta_id: Optional[uuid.UUID] = None
    cuenta_devolucion_compra_id: Optional[uuid.UUID] = None
    cuenta_ajuste_entrada_id: Optional[uuid.UUID] = None
    cuenta_ajuste_salida_id: Optional[uuid.UUID] = None


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = None
    tipo_id: Optional[uuid.UUID] = None
    familia_id: Optional[uuid.UUID] = None
    um_base_id: Optional[uuid.UUID] = None
    maneja_inventario: Optional[bool] = None
    maneja_series: Optional[bool] = None
    maneja_lotes: Optional[bool] = None
    cuenta_inventario_id: Optional[uuid.UUID] = None
    cuenta_costo_ventas_id: Optional[uuid.UUID] = None
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    cuenta_devolucion_venta_id: Optional[uuid.UUID] = None
    cuenta_devolucion_compra_id: Optional[uuid.UUID] = None
    cuenta_ajuste_entrada_id: Optional[uuid.UUID] = None
    cuenta_ajuste_salida_id: Optional[uuid.UUID] = None
    activo: Optional[bool] = None


class ProductoResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: Optional[str]
    tipo_id: uuid.UUID
    tipo_codigo: str
    tipo_nombre: str
    familia_id: Optional[uuid.UUID]
    familia_nombre: Optional[str]
    um_base_id: uuid.UUID
    um_base_codigo: str
    um_base_nombre: str
    maneja_inventario: bool
    maneja_series: bool
    maneja_lotes: bool
    cuenta_inventario_id: Optional[uuid.UUID]
    cuenta_inventario_display: Optional[str]
    cuenta_costo_ventas_id: Optional[uuid.UUID]
    cuenta_costo_ventas_display: Optional[str]
    cuenta_ingreso_id: Optional[uuid.UUID]
    cuenta_ingreso_display: Optional[str]
    cuenta_devolucion_venta_id: Optional[uuid.UUID]
    cuenta_devolucion_venta_display: Optional[str]
    cuenta_devolucion_compra_id: Optional[uuid.UUID]
    cuenta_devolucion_compra_display: Optional[str]
    cuenta_ajuste_entrada_id: Optional[uuid.UUID]
    cuenta_ajuste_entrada_display: Optional[str]
    cuenta_ajuste_salida_id: Optional[uuid.UUID]
    cuenta_ajuste_salida_display: Optional[str]
    activo: bool


# ---------------------------------------------------------------------------
# Producto — Unidades de medida alternas
# ---------------------------------------------------------------------------

class ProductoUmCreate(BaseModel):
    um_id: uuid.UUID
    factor: Decimal = Field(..., gt=0, decimal_places=6)
    es_compra: bool = False
    es_venta: bool = False


class ProductoUmUpdate(BaseModel):
    factor: Optional[Decimal] = Field(None, gt=0, decimal_places=6)
    es_compra: Optional[bool] = None
    es_venta: Optional[bool] = None


class ProductoUmResponse(BaseModel):
    id: uuid.UUID
    producto_id: uuid.UUID
    um_id: uuid.UUID
    um_codigo: str
    um_nombre: str
    factor: Decimal
    es_compra: bool
    es_venta: bool
    activo: bool


# ---------------------------------------------------------------------------
# Bodega
# ---------------------------------------------------------------------------

class BodegaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=1, max_length=100)
    direccion: Optional[str] = None
    responsable_id: Optional[uuid.UUID] = None


class BodegaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    direccion: Optional[str] = None
    responsable_id: Optional[uuid.UUID] = None
    activo: Optional[bool] = None


class BodegaResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    direccion: Optional[str]
    responsable_id: Optional[uuid.UUID]
    responsable_nombre: Optional[str] = None
    activo: bool
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Saldos de inventario
# ---------------------------------------------------------------------------

class SaldoProducto(BaseModel):
    producto_id: uuid.UUID
    producto_codigo: str
    producto_nombre: str
    um_base_codigo: str
    bodega_id: uuid.UUID
    bodega_nombre: str
    cantidad: Decimal
    costo_promedio: Decimal
    valor_total: Decimal


class SaldoListResponse(BaseModel):
    items: list[SaldoProducto]
    total: int
    pagina: int
    por_pagina: int


# ---------------------------------------------------------------------------
# Kardex
# ---------------------------------------------------------------------------

class KardexLinea(BaseModel):
    fecha: str
    movimiento_id: uuid.UUID
    numero: Optional[str]
    tipo: str
    descripcion: Optional[str]
    origen_tipo: Optional[str]
    origen_id: Optional[uuid.UUID]
    cantidad_entrada: Decimal
    cantidad_salida: Decimal
    costo_unitario: Decimal
    costo_total: Decimal
    saldo_cantidad: Decimal
    saldo_valor: Decimal
    costo_promedio: Decimal


class KardexResponse(BaseModel):
    producto_id: uuid.UUID
    producto_codigo: str
    producto_nombre: str
    bodega_id: Optional[uuid.UUID]
    bodega_nombre: Optional[str]
    lineas: list[KardexLinea]


# ---------------------------------------------------------------------------
# Movimientos
# ---------------------------------------------------------------------------

class MovimientoListItem(BaseModel):
    id: uuid.UUID
    numero: Optional[str]
    tipo: str
    fecha: str
    bodega_id: uuid.UUID
    bodega_nombre: str
    bodega_destino_nombre: Optional[str]
    descripcion: Optional[str]
    estado: str
    origen_tipo: Optional[str]
    origen_id: Optional[uuid.UUID]
    num_lineas: int
    costo_total: Decimal

class MovimientoListResponse(BaseModel):
    items: list[MovimientoListItem]
    total: int
    pagina: int
    por_pagina: int

class MovimientoLineaDetalle(BaseModel):
    id: uuid.UUID
    producto_id: uuid.UUID
    producto_codigo: str
    producto_nombre: str
    cantidad: Decimal
    um_id: uuid.UUID
    um_codigo: str
    costo_unitario: Decimal
    costo_total: Decimal

class MovimientoDetalle(BaseModel):
    id: uuid.UUID
    numero: Optional[str]
    tipo: str
    fecha: str
    bodega_id: uuid.UUID
    bodega_nombre: str
    bodega_destino_id: Optional[uuid.UUID]
    bodega_destino_nombre: Optional[str]
    descripcion: Optional[str]
    estado: str
    origen_tipo: Optional[str]
    origen_id: Optional[uuid.UUID]
    asiento_id: Optional[uuid.UUID]
    lineas: list[MovimientoLineaDetalle]
    costo_total: Decimal


# ---------------------------------------------------------------------------
# Movimiento manual (ajuste o traslado)
# ---------------------------------------------------------------------------

class MovimientoLineaCreate(BaseModel):
    producto_id: uuid.UUID
    cantidad: Decimal = Field(gt=0)
    um_id: uuid.UUID
    costo_unitario: Decimal = Field(ge=0)

class MovimientoManualCreate(BaseModel):
    tipo: str = Field(pattern="^(AJUSTE_ENTRADA|AJUSTE_SALIDA|TRASLADO)$")
    fecha: date
    bodega_id: uuid.UUID
    bodega_destino_id: Optional[uuid.UUID] = None  # solo para TRASLADO
    descripcion: Optional[str] = None
    lineas: list[MovimientoLineaCreate] = Field(min_length=1)
    publicar: bool = False

# Alias para compatibilidad
AjusteLineaCreate = MovimientoLineaCreate
AjusteCreate = MovimientoManualCreate
