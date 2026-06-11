import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Retenciones
# ---------------------------------------------------------------------------

class RetencionCreate(BaseModel):
    tipo: Literal["RETEFUENTE", "RETEICA", "RETEIVA"]
    concepto: str
    base: Decimal
    porcentaje: Decimal
    valor: Decimal
    cuenta_id: uuid.UUID


class RetencionResponse(BaseModel):
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


# ---------------------------------------------------------------------------
# Documento CxC
# ---------------------------------------------------------------------------

TipoDoc = Literal["FACTURA", "RECIBO", "NOTA_CREDITO", "NOTA_DEBITO", "ANTICIPO"]
EstadoDoc = Literal["borrador", "contabilizado", "anulado"]


class CxcDocumentoCreate(BaseModel):
    tipo: TipoDoc
    numero: str
    fecha: date
    fecha_vencimiento: Optional[date] = None
    tercero_id: uuid.UUID
    moneda_id: uuid.UUID
    trm: Optional[Decimal] = None
    subtotal: Decimal
    total_iva: Decimal = Decimal("0")
    total_retenciones: Decimal = Decimal("0")
    descripcion: Optional[str] = None
    retenciones: list[RetencionCreate] = []
    tarifa_iva_id: Optional[uuid.UUID] = None
    condicion_pago_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validar(self) -> "CxcDocumentoCreate":
        if self.tipo in ("FACTURA", "NOTA_DEBITO") and not self.fecha_vencimiento:
            raise ValueError("La fecha de vencimiento es obligatoria para FACTURA y NOTA_DEBITO")
        if self.fecha_vencimiento and self.fecha_vencimiento < self.fecha:
            raise ValueError("La fecha de vencimiento no puede ser anterior a la fecha del documento")
        if self.subtotal <= 0:
            raise ValueError("El subtotal debe ser mayor que cero")
        return self


class CxcDocumentoUpdate(BaseModel):
    fecha: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    tercero_id: Optional[uuid.UUID] = None
    moneda_id: Optional[uuid.UUID] = None
    trm: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    total_iva: Optional[Decimal] = None
    total_retenciones: Optional[Decimal] = None
    descripcion: Optional[str] = None
    retenciones: Optional[list[RetencionCreate]] = None
    tarifa_iva_id: Optional[uuid.UUID] = None
    condicion_pago_id: Optional[uuid.UUID] = None


class AnularRequest(BaseModel):
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_requerido(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El motivo de anulación es obligatorio")
        return v.strip()


class AplicarRequest(BaseModel):
    documento_credito_id: uuid.UUID  # recibo/nota/anticipo que paga
    documento_debito_id: uuid.UUID   # factura a saldar
    valor: Decimal
    fecha: date

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El valor a aplicar debe ser mayor que cero")
        return v


class CxcDocumentoResponse(BaseModel):
    id: uuid.UUID
    numero: str
    tipo: TipoDoc
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
    estado: EstadoDoc
    tarifa_iva_id: Optional[uuid.UUID] = None
    condicion_pago_id: Optional[uuid.UUID] = None
    asiento_id: Optional[uuid.UUID] = None
    asiento_modificado_manual: bool
    documento_origen_id: Optional[uuid.UUID] = None
    ban_cuenta_id: Optional[uuid.UUID] = None
    retenciones: list[RetencionResponse] = []
    creado_en: datetime
    creado_por: uuid.UUID
    model_config = {"from_attributes": True}


class CxcDocumentoListItem(BaseModel):
    id: uuid.UUID
    numero: str
    tipo: TipoDoc
    fecha: date
    fecha_vencimiento: Optional[date] = None
    tercero_nit: Optional[str] = None
    tercero_nombre: Optional[str] = None
    moneda_codigo: str
    total: Decimal
    saldo: Decimal
    estado: EstadoDoc
    dias_vencimiento: Optional[int] = None   # negativo = vencida, positivo = por vencer
    model_config = {"from_attributes": True}


class CxcListResponse(BaseModel):
    items: list[CxcDocumentoListItem]
    total: int
    pagina: int
    por_pagina: int


class ReciboAplicacionItem(BaseModel):
    factura_id: uuid.UUID
    valor: Decimal

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El valor a aplicar debe ser mayor que cero")
        return v


class ReciboCreate(BaseModel):
    fecha: date
    tercero_id: uuid.UUID
    ban_cuenta_id: uuid.UUID
    moneda_id: uuid.UUID
    trm: Optional[Decimal] = None
    valor_recibido: Decimal           # efectivo que entra al banco
    descripcion: Optional[str] = None
    retenciones: list[RetencionCreate] = []
    aplicaciones: list[ReciboAplicacionItem]

    @field_validator("valor_recibido")
    @classmethod
    def vr_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El valor recibido debe ser mayor que cero")
        return v

    @model_validator(mode="after")
    def validar_aplicacion_completa(self) -> "ReciboCreate":
        if not self.aplicaciones:
            raise ValueError("El recibo debe tener al menos una factura aplicada")
        total_retenciones = sum(r.valor for r in self.retenciones)
        total_aplicado = sum(a.valor for a in self.aplicaciones)
        esperado = self.valor_recibido + total_retenciones
        if abs(total_aplicado - esperado) > Decimal("0.01"):
            raise ValueError(
                f"La suma de aplicaciones ({total_aplicado}) debe igualar "
                f"valor recibido + retenciones ({esperado})"
            )
        return self


class AplicacionPendienteItem(BaseModel):
    id: uuid.UUID
    factura_id: uuid.UUID
    numero: str
    fecha: date
    fecha_vencimiento: Optional[date]
    total: Decimal
    saldo_original: Decimal   # saldo de la factura sin contar esta aplicación
    valor: Decimal
    model_config = {"from_attributes": True}


class FacturaPendienteItem(BaseModel):
    id: uuid.UUID
    numero: str
    fecha: date
    fecha_vencimiento: Optional[date]
    total: Decimal
    aplicado: Decimal
    saldo: Decimal
    dias_vencimiento: Optional[int] = None
    model_config = {"from_attributes": True}


class CxcResumenItem(BaseModel):
    tercero_id: uuid.UUID
    tercero_nit: Optional[str] = None
    tercero_nombre: Optional[str] = None
    corriente: Decimal
    dias_1_30: Decimal
    dias_31_60: Decimal
    dias_61_90: Decimal
    mas_90: Decimal
    total: Decimal


class CxcResumenResponse(BaseModel):
    fecha_corte: date
    items: list[CxcResumenItem]
    total_corriente: Decimal
    total_1_30: Decimal
    total_31_60: Decimal
    total_61_90: Decimal
    total_mas_90: Decimal
    total_general: Decimal
