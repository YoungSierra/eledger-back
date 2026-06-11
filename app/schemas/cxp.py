import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


TipoDoc = Literal["FACTURA", "COMPROBANTE", "NOTA_CREDITO", "NOTA_DEBITO", "ANTICIPO"]
EstadoDoc = Literal["borrador", "contabilizado", "anulado"]


class LineaRetencionCreate(BaseModel):
    tipo: Literal["RETEFUENTE", "RETEICA", "RETEIVA"]
    descripcion: str
    base: Decimal
    porcentaje: Decimal
    valor: Decimal
    cuenta_id: Optional[uuid.UUID] = None


class LineaRetencionResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    descripcion: str
    base: Decimal
    porcentaje: Decimal
    valor: Decimal
    cuenta_id: uuid.UUID
    cuenta_codigo: Optional[str] = None
    cuenta_nombre: Optional[str] = None
    model_config = {"from_attributes": True}


class CxpLineaCreate(BaseModel):
    orden: int = 1
    descripcion: str
    concepto_id: Optional[uuid.UUID] = None
    cuenta_id: Optional[uuid.UUID] = None
    subtotal: Decimal
    iva_pct: Decimal = Decimal("0")
    total_iva: Decimal = Decimal("0")
    total: Decimal
    centro_costo_id: Optional[uuid.UUID] = None
    iva_tipo: str = "NINGUNO"
    cuenta_iva_id: Optional[uuid.UUID] = None
    retenciones: list[LineaRetencionCreate] = []

    @model_validator(mode="after")
    def validar(self) -> "CxpLineaCreate":
        if self.concepto_id is None and self.cuenta_id is None:
            raise ValueError("Cada línea debe tener concepto o cuenta")
        if self.subtotal <= 0:
            raise ValueError("El subtotal de cada línea debe ser mayor que cero")
        if self.total_iva > 0 and not self.cuenta_iva_id:
            raise ValueError("Se requiere cuenta de IVA cuando hay IVA en la línea")
        return self


class CxpLineaResponse(BaseModel):
    id: uuid.UUID
    orden: int
    descripcion: str
    concepto_id: Optional[uuid.UUID] = None
    concepto_nombre: Optional[str] = None
    cuenta_id: Optional[uuid.UUID] = None
    cuenta_codigo: Optional[str] = None
    cuenta_nombre: Optional[str] = None
    subtotal: Decimal
    iva_pct: Decimal
    total_iva: Decimal
    total: Decimal
    centro_costo_id: Optional[uuid.UUID] = None
    iva_tipo: str
    cuenta_iva_id: Optional[uuid.UUID] = None
    cuenta_iva_codigo: Optional[str] = None
    retenciones: list[LineaRetencionResponse] = []
    model_config = {"from_attributes": True}


class CxpDocumentoCreate(BaseModel):
    tipo: TipoDoc = "FACTURA"
    numero_proveedor: Optional[str] = None
    fecha: date
    fecha_vencimiento: Optional[date] = None
    condicion_pago_id: Optional[uuid.UUID] = None
    tercero_id: uuid.UUID
    moneda_id: uuid.UUID
    trm: Optional[Decimal] = None
    descripcion: Optional[str] = None
    lineas: list[CxpLineaCreate]

    @model_validator(mode="after")
    def validar(self) -> "CxpDocumentoCreate":
        if self.tipo in ("FACTURA", "NOTA_DEBITO") and not self.fecha_vencimiento:
            raise ValueError("La fecha de vencimiento es obligatoria para FACTURA y NOTA_DEBITO")
        if self.fecha_vencimiento and self.fecha_vencimiento < self.fecha:
            raise ValueError("La fecha de vencimiento no puede ser anterior a la fecha del documento")
        if not self.lineas:
            raise ValueError("El documento debe tener al menos una línea")
        return self


class CxpDocumentoUpdate(BaseModel):
    numero_proveedor: Optional[str] = None
    fecha: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    condicion_pago_id: Optional[uuid.UUID] = None
    tercero_id: Optional[uuid.UUID] = None
    moneda_id: Optional[uuid.UUID] = None
    trm: Optional[Decimal] = None
    descripcion: Optional[str] = None
    lineas: Optional[list[CxpLineaCreate]] = None


class ComprobanteAplicacionItem(BaseModel):
    factura_id: uuid.UUID
    valor: Decimal

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El valor debe ser mayor que cero")
        return v


class ComprobanteCreate(BaseModel):
    fecha: date
    tercero_id: uuid.UUID
    ban_cuenta_id: uuid.UUID
    moneda_id: uuid.UUID
    trm: Optional[Decimal] = None
    valor_pagado: Decimal
    descripcion: Optional[str] = None
    aplicaciones: list[ComprobanteAplicacionItem]

    @field_validator("valor_pagado")
    @classmethod
    def vp_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El valor pagado debe ser mayor que cero")
        return v

    @model_validator(mode="after")
    def validar(self) -> "ComprobanteCreate":
        if not self.aplicaciones:
            raise ValueError("El comprobante debe tener al menos una factura aplicada")
        total_aplicado = sum(a.valor for a in self.aplicaciones)
        if abs(total_aplicado - self.valor_pagado) > Decimal("0.01"):
            raise ValueError(
                f"La suma de aplicaciones ({total_aplicado}) debe igualar el valor pagado ({self.valor_pagado})"
            )
        return self


class FacturaPendienteCxpItem(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    fecha_vencimiento: Optional[date]
    total: Decimal
    aplicado: Decimal
    saldo: Decimal
    dias_vencimiento: Optional[int] = None
    model_config = {"from_attributes": True}


class AplicacionPendienteCxpItem(BaseModel):
    id: uuid.UUID
    factura_id: uuid.UUID
    numero: str
    fecha: date
    fecha_vencimiento: Optional[date]
    total: Decimal
    saldo_original: Decimal
    valor: Decimal
    model_config = {"from_attributes": True}


class AnularCxpRequest(BaseModel):
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_requerido(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El motivo de anulación es obligatorio")
        return v.strip()


class CxpDocumentoResponse(BaseModel):
    id: uuid.UUID
    numero: str
    tipo: TipoDoc
    numero_proveedor: Optional[str] = None
    fecha: date
    fecha_vencimiento: Optional[date] = None
    periodo_id: uuid.UUID
    tercero_id: uuid.UUID
    tercero_nit: Optional[str] = None
    tercero_nombre: Optional[str] = None
    moneda_id: uuid.UUID
    moneda_codigo: str
    trm: Optional[Decimal] = None
    subtotal: Decimal
    total_iva: Decimal
    total_retenciones: Decimal
    total: Decimal
    saldo: Decimal
    descripcion: Optional[str] = None
    condicion_pago_id: Optional[uuid.UUID] = None
    ban_cuenta_id: Optional[uuid.UUID] = None
    estado: EstadoDoc
    asiento_id: Optional[uuid.UUID] = None
    asiento_modificado_manual: bool
    documento_origen_id: Optional[uuid.UUID] = None
    lineas: list[CxpLineaResponse] = []
    creado_en: datetime
    creado_por: uuid.UUID
    model_config = {"from_attributes": True}


class CxpDocumentoListItem(BaseModel):
    id: uuid.UUID
    numero: str
    tipo: TipoDoc
    numero_proveedor: Optional[str] = None
    fecha: date
    fecha_vencimiento: Optional[date] = None
    tercero_nit: Optional[str] = None
    tercero_nombre: Optional[str] = None
    moneda_codigo: str
    total: Decimal
    saldo: Decimal
    estado: EstadoDoc
    dias_vencimiento: Optional[int] = None
    model_config = {"from_attributes": True}


class CxpListResponse(BaseModel):
    items: list[CxpDocumentoListItem]
    total: int
    pagina: int
    por_pagina: int


class CxpResumenItem(BaseModel):
    tercero_id: uuid.UUID
    tercero_nit: Optional[str] = None
    tercero_nombre: Optional[str] = None
    corriente: Decimal
    dias_1_30: Decimal
    dias_31_60: Decimal
    dias_61_90: Decimal
    mas_90: Decimal
    total: Decimal


class CxpResumenResponse(BaseModel):
    fecha_corte: date
    items: list[CxpResumenItem]
    total_corriente: Decimal
    total_1_30: Decimal
    total_31_60: Decimal
    total_61_90: Decimal
    total_mas_90: Decimal
    total_general: Decimal
