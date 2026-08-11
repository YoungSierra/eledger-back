"""Schemas de los documentos de transporte marítimo.

Van en archivo aparte porque `schemas/ope.py` ya es grande y esto es un bloque
independiente. MBL y HBL comparten casi toda la ruta y las condiciones, así que
esa parte vive en una base común.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

TipoCargaType = Literal["FCL", "LCL"]
PagoFleteType = Literal["PREPAID", "COLLECT"]
OrigenBlType = Literal["RECIBIDO", "EMITIDO"]
EstadoHblType = Literal["BORRADOR", "EMITIDA", "ANULADA"]


class _BlBase(BaseModel):
    """Lo que comparten el maestro y la casa: ruta, fechas y condiciones."""

    booking_no: Optional[str] = None
    export_references: Optional[str] = None
    referencia_cliente: Optional[str] = None

    shipper_id: Optional[uuid.UUID] = None
    shipper_texto: Optional[str] = None
    consignee_id: Optional[uuid.UUID] = None
    consignee_texto: Optional[str] = None
    notify_id: Optional[uuid.UUID] = None
    notify_texto: Optional[str] = None

    pre_carriage_by: Optional[str] = None
    place_of_receipt: Optional[str] = None
    puerto_embarque_id: Optional[uuid.UUID] = None
    puerto_descarga_id: Optional[uuid.UUID] = None
    place_of_delivery: Optional[str] = None
    onward_inland_routing: Optional[str] = None
    buque: Optional[str] = None
    viaje: Optional[str] = None

    fecha_emision: Optional[date] = None
    lugar_emision: Optional[str] = None
    shipped_on_board: Optional[date] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    fecha_arribo: Optional[date] = None

    termino: Optional[str] = None
    tipo_carga: TipoCargaType = "FCL"
    tipo_pago_flete: PagoFleteType = "PREPAID"
    freight_to_be_paid_at: Optional[str] = None
    num_originales: Optional[int] = None
    declared_value: Optional[str] = None

    say_total: Optional[str] = None
    marcas: Optional[str] = None
    descripcion_mercancia: Optional[str] = None
    bultos_cantidad: Optional[int] = None
    bultos_clase: Optional[str] = None
    carrier_receipt: Optional[str] = None
    peso_bruto_kg: Optional[Decimal] = None
    cbm: Optional[Decimal] = None

    notas: Optional[str] = None


# ---------------------------------------------------------------------------
# MBL
# ---------------------------------------------------------------------------

class MblCreate(_BlBase):
    numero_bl: str
    naviera_id: Optional[uuid.UUID] = None
    agente_destino: Optional[str] = None
    tara_kg: Optional[Decimal] = None
    free_days: Optional[int] = None

    @field_validator("numero_bl")
    @classmethod
    def numero_obligatorio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El número de BL es obligatorio")
        return v.strip().upper()


class MblUpdate(MblCreate):
    numero_bl: Optional[str] = None       # type: ignore[assignment]


class MblResponse(MblCreate):
    id: uuid.UUID
    operacion_id: uuid.UUID
    naviera_nombre: Optional[str] = None
    puerto_embarque: Optional[str] = None
    puerto_descarga: Optional[str] = None
    shipper_nombre: Optional[str] = None
    consignee_nombre: Optional[str] = None
    # `total_*` y no `hbls`/`contenedores`: esos nombres chocan con las
    # relaciones del ORM y Pydantic intentaría validar la lista como entero.
    total_hbls: int = 0
    total_contenedores: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Contenedor
# ---------------------------------------------------------------------------

class ContenedorCreate(BaseModel):
    numero: str
    mbl_id: Optional[uuid.UUID] = None
    sello: Optional[str] = None
    tipo: Optional[str] = None
    tara_kg: Optional[Decimal] = None
    peso_bruto_kg: Optional[Decimal] = None
    cbm: Optional[Decimal] = None
    fecha_devolucion: Optional[date] = None
    notas: Optional[str] = None

    @field_validator("numero")
    @classmethod
    def numero_obligatorio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El número de contenedor es obligatorio")
        return v.strip().upper()


class ContenedorUpdate(ContenedorCreate):
    numero: Optional[str] = None          # type: ignore[assignment]


class ContenedorResponse(ContenedorCreate):
    id: uuid.UUID
    operacion_id: uuid.UUID
    mbl_numero: Optional[str] = None
    # `hbls_numeros` y no `hbls`: ese nombre choca con la relación del ORM.
    hbls_numeros: list[str] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# HBL
# ---------------------------------------------------------------------------

class HblContenedorLink(BaseModel):
    """Un contenedor dentro de un HBL. Lleva cifras propias: en LCL cada casa
    aporta su parte del mismo contenedor."""

    contenedor_id: uuid.UUID
    piezas: Optional[int] = None
    peso_kg: Optional[Decimal] = None
    cbm: Optional[Decimal] = None

    # Necesario para que Pydantic acepte la fila del ORM al armar la respuesta.
    model_config = {"from_attributes": True}


class HblContenedorDetalle(HblContenedorLink):
    # Con default porque la validación corre primero sobre la fila puente, que
    # no trae estos datos; el servicio los completa después desde el contenedor.
    numero: str = ""
    sello: Optional[str] = None
    tipo: Optional[str] = None


class BlCargoItem(BaseModel):
    orden: int = 1
    concepto: str
    tarifa: Optional[Decimal] = None
    unidad: Optional[str] = None
    moneda: str = "USD"
    valor: Optional[Decimal] = None
    pago: PagoFleteType = "PREPAID"

    model_config = {"from_attributes": True}


class HblCreate(_BlBase):
    numero_hbl: str
    mbl_id: Optional[uuid.UUID] = None
    cotizacion_id: Optional[uuid.UUID] = None
    origen: OrigenBlType = "RECIBIDO"
    emisor_id: Optional[uuid.UUID] = None
    emisor_texto: Optional[str] = None
    do_numero: Optional[str] = None
    consignee_a_la_orden: bool = False
    agente_entrega: Optional[str] = None
    contenedores: list[HblContenedorLink] = []
    cargos: list[BlCargoItem] = []

    @field_validator("numero_hbl")
    @classmethod
    def numero_obligatorio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El número de HBL es obligatorio")
        return v.strip().upper()


class HblUpdate(HblCreate):
    numero_hbl: Optional[str] = None      # type: ignore[assignment]
    contenedores: Optional[list[HblContenedorLink]] = None   # type: ignore[assignment]
    cargos: Optional[list[BlCargoItem]] = None               # type: ignore[assignment]


class HblResponse(_BlBase):
    id: uuid.UUID
    operacion_id: uuid.UUID
    mbl_id: Optional[uuid.UUID]
    mbl_numero: Optional[str] = None
    cotizacion_id: Optional[uuid.UUID]
    cotizacion_numero: Optional[str] = None
    cliente_nombre: Optional[str] = None

    numero_hbl: str
    origen: OrigenBlType
    emisor_id: Optional[uuid.UUID]
    emisor_texto: Optional[str]
    emisor_nombre: Optional[str] = None
    do_numero: Optional[str]
    consignee_a_la_orden: bool
    agente_entrega: Optional[str]

    puerto_embarque: Optional[str] = None
    puerto_descarga: Optional[str] = None
    shipper_nombre: Optional[str] = None
    consignee_nombre: Optional[str] = None

    estado: EstadoHblType
    emitido_por_nombre: Optional[str] = None
    emitido_en: Optional[datetime] = None
    anulado_por_nombre: Optional[str] = None
    anulado_en: Optional[datetime] = None
    anulado_motivo: Optional[str] = None

    contenedores: list[HblContenedorDetalle] = []
    cargos: list[BlCargoItem] = []

    model_config = {"from_attributes": True}


class AnularHblRequest(BaseModel):
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El motivo es obligatorio")
        return v.strip()


# ---------------------------------------------------------------------------
# Vista de la carpeta y búsqueda
# ---------------------------------------------------------------------------

class MaritimoCarpetaResponse(BaseModel):
    operacion_id: uuid.UUID
    mbls: list[MblResponse] = []
    hbls: list[HblResponse] = []
    contenedores: list[ContenedorResponse] = []


class MaritimoBusquedaItem(BaseModel):
    """Resultado del tracking: por número de BL, booking o contenedor."""

    operacion_id: uuid.UUID
    operacion_numero: str
    operacion_estado: str
    coincide_por: str          # BL, BOOKING o CONTENEDOR
    valor: str
    documento: str             # MBL, HBL o CONTENEDOR
    buque: Optional[str] = None
    viaje: Optional[str] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    fecha_arribo: Optional[date] = None
    clientes: list[str] = []
