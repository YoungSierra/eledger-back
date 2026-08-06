from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel


class NomEmpleadoCreate(BaseModel):
    tipo_documento: str = "CC"
    numero_documento: str
    primer_nombre: str
    otros_nombres: Optional[str] = None
    primer_apellido: str
    segundo_apellido: Optional[str] = None
    cargo: Optional[str] = None
    salario_basico: Decimal = Decimal("0")
    dias_trabajados: Decimal = Decimal("0")
    sueldo: Decimal = Decimal("0")
    auxilio_transporte: Decimal = Decimal("0")
    horas_extra: Decimal = Decimal("0")
    bonificaciones: Decimal = Decimal("0")
    comisiones: Decimal = Decimal("0")
    devengados_extra: Optional[dict] = None
    salud: Decimal = Decimal("0")
    pension: Decimal = Decimal("0")
    fondo_solidaridad: Decimal = Decimal("0")
    retencion_fuente: Decimal = Decimal("0")
    deducciones_extra: Optional[dict] = None


class NomEmpleadoResponse(NomEmpleadoCreate):
    id: uuid.UUID
    orden: int
    total_devengado: Decimal
    total_deducciones: Decimal
    neto: Decimal

    model_config = {"from_attributes": True}


class NomPeriodoCreate(BaseModel):
    tipo: str = "NOMINA"
    periodo_pago_inicio: date
    periodo_pago_fin: date
    fecha_generacion: date
    notas: Optional[str] = None
    empleados: list[NomEmpleadoCreate] = []


class NomPeriodoUpdate(BaseModel):
    tipo: Optional[str] = None
    periodo_pago_inicio: Optional[date] = None
    periodo_pago_fin: Optional[date] = None
    fecha_generacion: Optional[date] = None
    notas: Optional[str] = None
    empleados: Optional[list[NomEmpleadoCreate]] = None


class AnularNominaRequest(BaseModel):
    motivo: str


class NomEventoResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    estado: Optional[str] = None
    mensaje: Optional[str] = None
    creado_en: datetime

    model_config = {"from_attributes": True}


class NomPeriodoResponse(BaseModel):
    id: uuid.UUID
    numero: str
    tipo: str
    periodo_pago_inicio: date
    periodo_pago_fin: date
    fecha_generacion: date
    periodo_id: uuid.UUID
    total_devengado: Decimal
    total_deducciones: Decimal
    total_neto: Decimal
    notas: Optional[str] = None
    estado: str
    cune: Optional[str] = None
    dian_estado: Optional[str] = None
    dian_mensaje: Optional[str] = None
    xml_key: Optional[str] = None
    empleados: list[NomEmpleadoResponse] = []
    eventos: list[NomEventoResponse] = []
    creado_en: datetime
    creado_por: uuid.UUID

    model_config = {"from_attributes": True}


class NomPeriodoListItem(BaseModel):
    id: uuid.UUID
    numero: str
    tipo: str
    periodo_pago_inicio: date
    periodo_pago_fin: date
    fecha_generacion: date
    empleados_count: int
    total_devengado: Decimal
    total_deducciones: Decimal
    total_neto: Decimal
    estado: str
    dian_estado: Optional[str] = None
    creado_en: datetime

    model_config = {"from_attributes": True}


class NomListResponse(BaseModel):
    items: list[NomPeriodoListItem]
    total: int
    pagina: int
    por_pagina: int


class ImportarExcelResponse(BaseModel):
    empleados: list[NomEmpleadoCreate]
    filas_leidas: int
    avisos: list[str] = []
