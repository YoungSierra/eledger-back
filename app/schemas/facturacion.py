from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel


class RetencionFacCreate(BaseModel):
    tipo: str
    concepto: str
    base: Decimal
    porcentaje: Decimal
    valor: Decimal
    cuenta_id: uuid.UUID


class RetencionFacResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    concepto: str
    base: Decimal
    porcentaje: Decimal
    valor: Decimal
    cuenta_id: uuid.UUID
    cuenta_codigo: Optional[str] = None
    cuenta_nombre: Optional[str] = None

    model_config = {"from_attributes": True}


class LineaFacCreate(BaseModel):
    producto_id: Optional[uuid.UUID] = None
    descripcion: str
    cantidad: Decimal
    um_id: Optional[uuid.UUID] = None
    precio_unitario: Decimal
    descuento_pct: Decimal = Decimal("0")
    descuento_valor: Decimal = Decimal("0")
    subtotal: Decimal
    iva_tipo: str = "NINGUNO"
    iva_pct: Decimal = Decimal("0")
    total_iva: Decimal = Decimal("0")
    cuenta_iva_id: Optional[uuid.UUID] = None
    total: Decimal
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    centro_costo_id: Optional[uuid.UUID] = None
    cotizacion_linea_id: Optional[uuid.UUID] = None
    monto_cotizacion: Optional[Decimal] = None


class LineaFacResponse(BaseModel):
    id: uuid.UUID
    orden: int
    producto_id: Optional[uuid.UUID] = None
    producto_codigo: Optional[str] = None
    producto_nombre: Optional[str] = None
    descripcion: str
    cantidad: Decimal
    um_id: Optional[uuid.UUID] = None
    um_codigo: Optional[str] = None
    precio_unitario: Decimal
    descuento_pct: Decimal
    descuento_valor: Decimal
    subtotal: Decimal
    iva_tipo: str
    iva_pct: Decimal
    total_iva: Decimal
    cuenta_iva_id: Optional[uuid.UUID] = None
    cuenta_iva_codigo: Optional[str] = None
    total: Decimal
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    cuenta_ingreso_codigo: Optional[str] = None
    cuenta_ingreso_nombre: Optional[str] = None
    centro_costo_id: Optional[uuid.UUID] = None
    centro_costo_codigo: Optional[str] = None
    centro_costo_nombre: Optional[str] = None
    cotizacion_linea_id: Optional[uuid.UUID] = None
    monto_cotizacion: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class FacFacturaCreate(BaseModel):
    fecha: date
    fecha_vencimiento: date
    cliente_id: uuid.UUID
    cotizacion_id: Optional[uuid.UUID] = None
    moneda_id: uuid.UUID
    trm: Optional[Decimal] = None
    condicion_pago_id: Optional[uuid.UUID] = None
    notas: Optional[str] = None
    lineas: list[LineaFacCreate]
    retenciones: list[RetencionFacCreate] = []


class FacFacturaUpdate(BaseModel):
    fecha: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    cliente_id: Optional[uuid.UUID] = None
    moneda_id: Optional[uuid.UUID] = None
    trm: Optional[Decimal] = None
    condicion_pago_id: Optional[uuid.UUID] = None
    notas: Optional[str] = None
    lineas: Optional[list[LineaFacCreate]] = None
    retenciones: Optional[list[RetencionFacCreate]] = None


class AnularFacturaRequest(BaseModel):
    motivo: str


class FacturarCotizacionLineaReq(BaseModel):
    cotizacion_linea_id: uuid.UUID
    monto: Decimal   # en la moneda NATIVA de la línea de cotización


class FacturarCotizacionRequest(BaseModel):
    moneda: str      # "COP" | "USD" (moneda de la factura)
    fecha: date
    fecha_vencimiento: date
    condicion_pago_id: Optional[uuid.UUID] = None
    notas: Optional[str] = None
    lineas: list[FacturarCotizacionLineaReq]


class FacFacturaResponse(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    fecha_vencimiento: date
    periodo_id: uuid.UUID
    cliente_id: uuid.UUID
    cliente_nit: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_direccion: Optional[str] = None
    cliente_ciudad: Optional[str] = None
    cliente_departamento: Optional[str] = None
    cliente_telefono: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_regimen: Optional[str] = None
    cliente_responsable_iva: bool = False
    cotizacion_id: Optional[uuid.UUID] = None
    cotizacion_numero: Optional[str] = None
    moneda_id: uuid.UUID
    moneda_codigo: str
    trm: Optional[Decimal] = None
    condicion_pago_id: Optional[uuid.UUID] = None
    condicion_pago_nombre: Optional[str] = None
    subtotal: Decimal
    total_descuentos: Decimal
    total_iva: Decimal
    total_retenciones: Decimal
    total: Decimal
    notas: Optional[str] = None
    estado: str
    asiento_id: Optional[uuid.UUID] = None
    asiento_modificado_manual: bool
    cxc_documento_id: Optional[uuid.UUID] = None
    cufe: Optional[str] = None
    fecha_dian: Optional[datetime] = None
    dian_estado: Optional[str] = None
    lineas: list[LineaFacResponse] = []
    retenciones: list[RetencionFacResponse] = []
    creado_en: datetime
    creado_por: uuid.UUID

    model_config = {"from_attributes": True}


class FacFacturaListItem(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    fecha_vencimiento: date
    cliente_nit: Optional[str] = None
    cliente_nombre: Optional[str] = None
    moneda_codigo: str
    subtotal: Decimal
    total_iva: Decimal
    total_retenciones: Decimal
    total: Decimal
    estado: str
    dian_estado: Optional[str] = None
    dias_vencimiento: Optional[int] = None

    model_config = {"from_attributes": True}


class FacListResponse(BaseModel):
    items: list[FacFacturaListItem]
    total: int
    pagina: int
    por_pagina: int
