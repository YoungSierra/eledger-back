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
    valor_tercero: bool = False
    proveedor_id: Optional[uuid.UUID] = None


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
    valor_tercero: bool = False
    proveedor_id: Optional[uuid.UUID] = None
    proveedor_nombre: Optional[str] = None
    # Equivalente en moneda funcional cuando la factura está en otra moneda.
    # Lo calcula el backend con el MISMO redondeo del asiento, para que la
    # impresión y la contabilidad no difieran en centavos. None si no aplica.
    precio_unitario_func: Optional[Decimal] = None
    subtotal_func: Optional[Decimal] = None
    total_iva_func: Optional[Decimal] = None
    total_func: Optional[Decimal] = None

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


class PreviewAsientoLinea(BaseModel):
    cuenta_codigo: Optional[str] = None
    cuenta_nombre: Optional[str] = None
    tercero_nombre: Optional[str] = None
    centro_costo: Optional[str] = None
    debito: Decimal = Decimal("0")
    credito: Decimal = Decimal("0")
    # Lo que REALMENTE suma en los libros. Solo viene cuando el documento está
    # en moneda extranjera; si no, coincide con débito/crédito y se omite.
    debito_funcional: Optional[Decimal] = None
    credito_funcional: Optional[Decimal] = None


class PreviewAsientoResponse(BaseModel):
    lineas: list[PreviewAsientoLinea]
    total_debito: Decimal
    total_credito: Decimal
    cuadra: bool
    moneda_codigo: Optional[str] = None
    avisos: list[str] = []
    asiento_numero: Optional[int] = None
    # Moneda funcional y totales convertidos (None si el documento ya está en ella).
    moneda_funcional_codigo: Optional[str] = None
    trm: Optional[Decimal] = None
    total_debito_funcional: Optional[Decimal] = None
    total_credito_funcional: Optional[Decimal] = None


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
    numero_dian: Optional[str] = None
    xml_key: Optional[str] = None
    pdf_key: Optional[str] = None
    # Totales en moneda funcional (solo si la factura está en moneda extranjera).
    moneda_funcional_codigo: Optional[str] = None
    subtotal_func: Optional[Decimal] = None
    total_descuentos_func: Optional[Decimal] = None
    total_iva_func: Optional[Decimal] = None
    total_retenciones_func: Optional[Decimal] = None
    total_func: Optional[Decimal] = None
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
    saldo: Optional[Decimal] = None
    pagada: bool = False
    creado_en: datetime

    model_config = {"from_attributes": True}


class FacListResponse(BaseModel):
    items: list[FacFacturaListItem]
    total: int
    pagina: int
    por_pagina: int
