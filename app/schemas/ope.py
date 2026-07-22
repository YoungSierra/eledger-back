import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Tipos enumerados
# ---------------------------------------------------------------------------

SeccionType = Literal[
    "TRANSPORTE_INTERNACIONAL",
    "GASTOS_ORIGEN",
    "GASTOS_DESTINO",
    "ADUANA",
    "TRANSPORTE_TERRESTRE",
    "ALMACENAMIENTO",
    "SEGURO",
]
TipoCalculoType = Literal["POR_KG", "POR_EMBARQUE", "PORCENTAJE"]
ModalidadType = Literal["AEREA", "MARITIMA", "TERRESTRE"]
MonedaType = Literal["USD", "COP"]
TipoOperacionType = Literal["IMPORTACION", "EXPORTACION"]
IncotermType = Literal["EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"]
EstadoCotizacionType = Literal["BORRADOR", "ENVIADA", "APROBADA", "RECHAZADA", "VENCIDA"]
EstadoOperacionType = Literal["ABIERTA", "EN_CURSO", "CERRADA", "CANCELADA"]
EstadoDocTransporteType = Literal["BORRADOR", "EMITIDA", "ANULADA"]
EstadoDocOpeType = Literal["PENDIENTE", "RECIBIDO", "APROBADO"]
TipoEventoType = Literal["STATUS", "DOCUMENTO_RECIBIDO", "NOTA", "RESERVA", "APERTURA", "CIERRE"]
TipoDocumentoOpeType = Literal["FACTURA_COMERCIAL", "LISTA_EMPAQUE", "CERTIFICADO_ORIGEN", "OTRO"]


# ---------------------------------------------------------------------------
# Aerolínea
# ---------------------------------------------------------------------------

class OpeAerolineaCreate(BaseModel):
    codigo_iata: str
    nombre: str
    modalidad: ModalidadType

    @field_validator("codigo_iata")
    @classmethod
    def codigo_upper(cls, v: str) -> str:
        return v.strip().upper()


class OpeAerolineaUpdate(BaseModel):
    nombre: Optional[str] = None
    modalidad: Optional[ModalidadType] = None
    activo: Optional[bool] = None


class OpeAerolineaResponse(BaseModel):
    id: uuid.UUID
    codigo_iata: str
    nombre: str
    modalidad: ModalidadType
    activo: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Aeropuerto
# ---------------------------------------------------------------------------

class OpeAeropuertoCreate(BaseModel):
    codigo_iata: str
    nombre: str
    ciudad: str
    pais: str
    modalidad: ModalidadType

    @field_validator("codigo_iata")
    @classmethod
    def codigo_upper(cls, v: str) -> str:
        return v.strip().upper()


class OpeAeropuertoUpdate(BaseModel):
    nombre: Optional[str] = None
    ciudad: Optional[str] = None
    pais: Optional[str] = None
    modalidad: Optional[ModalidadType] = None
    activo: Optional[bool] = None


class OpeAeropuertoResponse(BaseModel):
    id: uuid.UUID
    codigo_iata: str
    nombre: str
    ciudad: str
    pais: str
    modalidad: ModalidadType
    activo: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Concepto tarifario
# ---------------------------------------------------------------------------

class OpeConceptoCreate(BaseModel):
    nombre: str
    seccion: SeccionType
    tipo_calculo: TipoCalculoType
    moneda: MonedaType
    cuenta_id: Optional[uuid.UUID] = None
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    tarifa_iva_id: Optional[uuid.UUID] = None


class OpeConceptoUpdate(BaseModel):
    nombre: Optional[str] = None
    seccion: Optional[SeccionType] = None
    tipo_calculo: Optional[TipoCalculoType] = None
    moneda: Optional[MonedaType] = None
    cuenta_id: Optional[uuid.UUID] = None
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    tarifa_iva_id: Optional[uuid.UUID] = None
    activo: Optional[bool] = None


class OpeConceptoResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    seccion: SeccionType
    tipo_calculo: TipoCalculoType
    moneda: MonedaType
    cuenta_id: Optional[uuid.UUID]
    cuenta_ingreso_id: Optional[uuid.UUID] = None
    cuenta_ingreso_nombre: Optional[str] = None
    tarifa_iva_id: Optional[uuid.UUID] = None
    tarifa_iva_nombre: Optional[str] = None
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Línea de cotización
# ---------------------------------------------------------------------------

class OpeCotizacionLineaCreate(BaseModel):
    seccion: SeccionType
    orden: int
    concepto_id: Optional[uuid.UUID] = None
    descripcion: str
    tipo_calculo: TipoCalculoType
    valor_unitario: Decimal
    costo_unitario: Decimal
    base: Decimal = Decimal("1")
    minimo: Optional[Decimal] = None
    moneda: MonedaType
    proveedor_id: Optional[uuid.UUID] = None
    condiciones_costo: Optional[str] = None
    notas: Optional[str] = None

    @field_validator("valor_unitario", "costo_unitario", "base")
    @classmethod
    def no_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("El valor no puede ser negativo")
        return v

    @field_validator("minimo")
    @classmethod
    def minimo_no_negativo(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("El mínimo no puede ser negativo")
        return v


class OpeCotizacionLineaUpdate(BaseModel):
    seccion: Optional[SeccionType] = None
    orden: Optional[int] = None
    concepto_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = None
    tipo_calculo: Optional[TipoCalculoType] = None
    valor_unitario: Optional[Decimal] = None
    costo_unitario: Optional[Decimal] = None
    base: Optional[Decimal] = None
    minimo: Optional[Decimal] = None
    moneda: Optional[MonedaType] = None
    proveedor_id: Optional[uuid.UUID] = None
    condiciones_costo: Optional[str] = None
    notas: Optional[str] = None


class OpeCotizacionLineaResponse(BaseModel):
    id: uuid.UUID
    cotizacion_id: uuid.UUID
    seccion: SeccionType
    orden: int
    concepto_id: Optional[uuid.UUID]
    descripcion: str
    tipo_calculo: TipoCalculoType
    valor_unitario: Decimal
    costo_unitario: Decimal
    base: Decimal
    minimo: Optional[Decimal]
    total_venta: Decimal
    total_costo: Decimal
    moneda: MonedaType
    proveedor_id: Optional[uuid.UUID]
    condiciones_costo: Optional[str]
    notas: Optional[str]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Cotización — encabezado
# ---------------------------------------------------------------------------

class OpeCotizacionCreate(BaseModel):
    cliente_id: uuid.UUID
    fecha: date
    fecha_vigencia: date
    tipo_operacion: TipoOperacionType
    modalidad: ModalidadType = "AEREA"
    origen: str
    destino: str
    aerolinea_id: Optional[uuid.UUID] = None
    incoterm: Optional[IncotermType] = None
    piezas: Optional[int] = None
    peso_kg: Optional[Decimal] = None
    valor_mercancia: Optional[Decimal] = None
    moneda_mercancia: MonedaType = "USD"
    valor_cif: Optional[Decimal] = None
    trm: Optional[Decimal] = None  # si None el service lo jala de adm_trm
    notas: Optional[str] = None
    asesor_id: Optional[uuid.UUID] = None
    lineas: list[OpeCotizacionLineaCreate] = []

    @model_validator(mode="after")
    def fecha_vigencia_posterior(self) -> "OpeCotizacionCreate":
        if self.fecha_vigencia < self.fecha:
            raise ValueError("fecha_vigencia debe ser igual o posterior a fecha")
        return self


class OpeCotizacionUpdate(BaseModel):
    cliente_id: Optional[uuid.UUID] = None
    fecha: Optional[date] = None
    fecha_vigencia: Optional[date] = None
    tipo_operacion: Optional[TipoOperacionType] = None
    modalidad: Optional[ModalidadType] = None
    origen: Optional[str] = None
    destino: Optional[str] = None
    aerolinea_id: Optional[uuid.UUID] = None
    incoterm: Optional[IncotermType] = None
    piezas: Optional[int] = None
    peso_kg: Optional[Decimal] = None
    valor_mercancia: Optional[Decimal] = None
    moneda_mercancia: Optional[MonedaType] = None
    valor_cif: Optional[Decimal] = None
    trm: Optional[Decimal] = None
    notas: Optional[str] = None
    lineas: Optional[list[OpeCotizacionLineaCreate]] = None


class OpeCotizacionResponse(BaseModel):
    id: uuid.UUID
    numero: str
    cliente_id: uuid.UUID
    fecha: date
    fecha_vigencia: date
    tipo_operacion: TipoOperacionType
    modalidad: ModalidadType
    origen: str
    destino: str
    aerolinea_id: Optional[uuid.UUID]
    incoterm: Optional[IncotermType]
    piezas: Optional[int]
    peso_kg: Optional[Decimal]
    valor_mercancia: Optional[Decimal]
    moneda_mercancia: MonedaType
    valor_cif: Optional[Decimal]
    trm: Optional[Decimal]
    notas: Optional[str]
    asesor_id: Optional[uuid.UUID] = None
    asesor_nombre: Optional[str] = None
    operacion_id: Optional[uuid.UUID] = None
    estado: EstadoCotizacionType
    activo: bool
    creado_en: datetime
    modificado_en: Optional[datetime]
    lineas: list[OpeCotizacionLineaResponse] = []

    model_config = {"from_attributes": True}


class OpeCotizacionSummary(BaseModel):
    """Vista de lista — sin líneas."""
    id: uuid.UUID
    numero: str
    cliente_id: uuid.UUID
    cliente_nombre: str
    fecha: date
    fecha_vigencia: date
    tipo_operacion: TipoOperacionType
    modalidad: ModalidadType
    origen: str
    destino: str
    asesor_id: Optional[uuid.UUID] = None
    asesor_nombre: Optional[str] = None
    operacion_id: Optional[uuid.UUID] = None
    estado: EstadoCotizacionType
    trm: Optional[Decimal]
    creado_en: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Margen de cotización (vista calculada)
# ---------------------------------------------------------------------------

class LineaMargenResponse(BaseModel):
    seccion: SeccionType
    descripcion: str
    moneda: MonedaType
    total_venta: Decimal
    total_costo: Decimal
    margen: Decimal


class SeccionMargenResponse(BaseModel):
    seccion: SeccionType
    total_venta_cop: Decimal
    total_costo_cop: Decimal
    margen_cop: Decimal


class OpeCotizacionMargenResponse(BaseModel):
    cotizacion_id: uuid.UUID
    numero: str
    trm: Decimal
    lineas: list[LineaMargenResponse]
    secciones: list[SeccionMargenResponse]
    total_venta_cop: Decimal
    total_costo_cop: Decimal
    margen_cop: Decimal
    margen_pct: Decimal  # (margen / venta) * 100


# ---------------------------------------------------------------------------
# Operación
# ---------------------------------------------------------------------------

class ClienteResumen(BaseModel):
    id: uuid.UUID
    nombre: str
    nit: Optional[str] = None


class OpeOperacionResponse(BaseModel):
    id: uuid.UUID
    numero: str
    fecha_apertura: date
    estado: EstadoOperacionType
    aerolinea_id: Optional[uuid.UUID]
    piezas: Optional[int]
    peso_kg: Optional[Decimal]
    activo: bool
    creado_en: datetime
    clientes: list[ClienteResumen] = []

    model_config = {"from_attributes": True}


class OpeOperacionUpdate(BaseModel):
    estado: Optional[EstadoOperacionType] = None
    aerolinea_id: Optional[uuid.UUID] = None
    piezas: Optional[int] = None
    peso_kg: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# HAWB
# ---------------------------------------------------------------------------

class OpeHawbCreate(BaseModel):
    numero_hawb: str
    mawb_id: Optional[uuid.UUID] = None
    cotizacion_id: Optional[uuid.UUID] = None
    shipper_id: uuid.UUID
    shipper_account: Optional[str] = None
    consignee_id: uuid.UUID
    consignee_account: Optional[str] = None
    aeropuerto_origen_id: Optional[uuid.UUID] = None
    aeropuerto_destino_id: Optional[uuid.UUID] = None
    aerolinea_id: Optional[uuid.UUID] = None
    vuelo: Optional[str] = None
    fecha_vuelo: Optional[date] = None
    trm: Optional[Decimal] = None
    agent_iata_code: Optional[str] = None
    agent_account_no: Optional[str] = None
    tipo_pago_flete: Literal["PPD", "COLL"] = "PPD"
    tipo_pago_otros: Literal["PPD", "COLL"] = "PPD"
    moneda: str = "USD"
    valor_declarado_transporte: str = "NVD"
    valor_declarado_aduana: str = "NVD"
    monto_seguro: Optional[str] = None
    info_manejo: Optional[str] = None
    clase_tarifa: Optional[str] = None
    piezas: Optional[int] = None
    peso_bruto_kg: Optional[Decimal] = None
    peso_cargable_kg: Optional[Decimal] = None
    tarifa: Optional[str] = None
    total_carga: Optional[str] = None
    descripcion_mercancia: Optional[str] = None
    dimensiones: Optional[str] = None
    cargo_peso: Optional[str] = None
    cargo_valuacion: Optional[str] = None
    tax: Optional[str] = None
    otros_cargos: Optional[str] = None
    fecha_ejecucion: Optional[date] = None
    lugar_ejecucion: Optional[str] = None


class OpeHawbUpdate(BaseModel):
    numero_hawb: Optional[str] = None
    mawb_id: Optional[uuid.UUID] = None
    cotizacion_id: Optional[uuid.UUID] = None
    shipper_id: Optional[uuid.UUID] = None
    shipper_account: Optional[str] = None
    consignee_id: Optional[uuid.UUID] = None
    consignee_account: Optional[str] = None
    aeropuerto_origen_id: Optional[uuid.UUID] = None
    aeropuerto_destino_id: Optional[uuid.UUID] = None
    aerolinea_id: Optional[uuid.UUID] = None
    vuelo: Optional[str] = None
    fecha_vuelo: Optional[date] = None
    trm: Optional[Decimal] = None
    agent_iata_code: Optional[str] = None
    agent_account_no: Optional[str] = None
    tipo_pago_flete: Optional[Literal["PPD", "COLL"]] = None
    tipo_pago_otros: Optional[Literal["PPD", "COLL"]] = None
    moneda: Optional[str] = None
    valor_declarado_transporte: Optional[str] = None
    valor_declarado_aduana: Optional[str] = None
    monto_seguro: Optional[str] = None
    info_manejo: Optional[str] = None
    clase_tarifa: Optional[str] = None
    piezas: Optional[int] = None
    peso_bruto_kg: Optional[Decimal] = None
    peso_cargable_kg: Optional[Decimal] = None
    tarifa: Optional[str] = None
    total_carga: Optional[str] = None
    descripcion_mercancia: Optional[str] = None
    dimensiones: Optional[str] = None
    cargo_peso: Optional[str] = None
    cargo_valuacion: Optional[str] = None
    tax: Optional[str] = None
    otros_cargos: Optional[str] = None
    fecha_ejecucion: Optional[date] = None
    lugar_ejecucion: Optional[str] = None


class OpeHawbResponse(BaseModel):
    id: uuid.UUID
    operacion_id: uuid.UUID
    mawb_id: Optional[uuid.UUID]
    cotizacion_id: Optional[uuid.UUID] = None
    cotizacion_numero: Optional[str] = None
    cliente_nombre: Optional[str] = None
    numero_hawb: str
    shipper_id: uuid.UUID
    shipper_account: Optional[str]
    consignee_id: uuid.UUID
    consignee_account: Optional[str]
    aeropuerto_origen_id: Optional[uuid.UUID]
    aeropuerto_destino_id: Optional[uuid.UUID]
    aerolinea_id: Optional[uuid.UUID]
    vuelo: Optional[str]
    fecha_vuelo: Optional[date]
    trm: Optional[Decimal]
    agent_iata_code: Optional[str]
    agent_account_no: Optional[str]
    tipo_pago_flete: str
    tipo_pago_otros: str
    moneda: str
    valor_declarado_transporte: str
    valor_declarado_aduana: str
    monto_seguro: Optional[str]
    info_manejo: Optional[str]
    clase_tarifa: Optional[str]
    piezas: Optional[int]
    peso_bruto_kg: Optional[Decimal]
    peso_cargable_kg: Optional[Decimal]
    tarifa: Optional[str]
    total_carga: Optional[str]
    descripcion_mercancia: Optional[str]
    dimensiones: Optional[str]
    cargo_peso: Optional[str]
    cargo_valuacion: Optional[str]
    tax: Optional[str]
    otros_cargos: Optional[str]
    fecha_ejecucion: Optional[date]
    lugar_ejecucion: Optional[str]
    estado: EstadoDocTransporteType
    emitido_por: Optional[uuid.UUID] = None
    emitido_por_nombre: Optional[str] = None
    emitido_en: Optional[datetime] = None
    anulado_por: Optional[uuid.UUID] = None
    anulado_por_nombre: Optional[str] = None
    anulado_en: Optional[datetime] = None
    anulado_motivo: Optional[str] = None
    creado_en: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# MAWB
# ---------------------------------------------------------------------------

class OpeMawbCreate(BaseModel):
    prefix: Optional[str] = None
    numero_mawb: str
    consignee_id: Optional[uuid.UUID] = None
    shipper_account: Optional[str] = None
    consignee_account: Optional[str] = None
    aerolinea_id: Optional[uuid.UUID] = None
    aeropuerto_origen_id: Optional[uuid.UUID] = None
    aeropuerto_destino_id: Optional[uuid.UUID] = None
    vuelo: Optional[str] = None
    fecha_vuelo: Optional[date] = None
    trm: Optional[Decimal] = None
    agent_iata_code: Optional[str] = None
    agent_account_no: Optional[str] = None
    tipo_pago_flete: Literal["PPD", "COLL"] = "PPD"
    tipo_pago_otros: Literal["PPD", "COLL"] = "PPD"
    moneda_flete: MonedaType = "USD"
    valor_declarado_transporte: str = "NVD"
    valor_declarado_aduana: str = "NVD"
    monto_seguro: Optional[str] = None
    info_manejo: Optional[str] = None
    clase_tarifa: Optional[str] = None
    piezas: Optional[int] = None
    peso_bruto_kg: Optional[Decimal] = None
    peso_cargable_kg: Optional[Decimal] = None
    tarifa_por_kg: Optional[Decimal] = None
    descripcion_mercancia: Optional[str] = None
    dimensiones: Optional[str] = None
    flete_total: Optional[Decimal] = None
    fsc: Optional[Decimal] = None
    due_carrier: Optional[Decimal] = None
    cargo_valuacion: Optional[str] = None
    tax: Optional[str] = None
    otros_due_agent: Optional[Decimal] = None
    otros_due_carrier: Optional[Decimal] = None
    total_prepaid: Optional[Decimal] = None
    fecha_ejecucion: Optional[date] = None
    lugar_ejecucion: Optional[str] = None


class OpeMawbUpdate(BaseModel):
    prefix: Optional[str] = None
    numero_mawb: Optional[str] = None
    consignee_id: Optional[uuid.UUID] = None
    shipper_account: Optional[str] = None
    consignee_account: Optional[str] = None
    aerolinea_id: Optional[uuid.UUID] = None
    aeropuerto_origen_id: Optional[uuid.UUID] = None
    aeropuerto_destino_id: Optional[uuid.UUID] = None
    vuelo: Optional[str] = None
    fecha_vuelo: Optional[date] = None
    trm: Optional[Decimal] = None
    agent_iata_code: Optional[str] = None
    agent_account_no: Optional[str] = None
    tipo_pago_flete: Optional[Literal["PPD", "COLL"]] = None
    tipo_pago_otros: Optional[Literal["PPD", "COLL"]] = None
    moneda_flete: Optional[MonedaType] = None
    valor_declarado_transporte: Optional[str] = None
    valor_declarado_aduana: Optional[str] = None
    monto_seguro: Optional[str] = None
    info_manejo: Optional[str] = None
    clase_tarifa: Optional[str] = None
    piezas: Optional[int] = None
    peso_bruto_kg: Optional[Decimal] = None
    peso_cargable_kg: Optional[Decimal] = None
    tarifa_por_kg: Optional[Decimal] = None
    descripcion_mercancia: Optional[str] = None
    dimensiones: Optional[str] = None
    flete_total: Optional[Decimal] = None
    fsc: Optional[Decimal] = None
    due_carrier: Optional[Decimal] = None
    cargo_valuacion: Optional[str] = None
    tax: Optional[str] = None
    otros_due_agent: Optional[Decimal] = None
    otros_due_carrier: Optional[Decimal] = None
    total_prepaid: Optional[Decimal] = None
    fecha_ejecucion: Optional[date] = None
    lugar_ejecucion: Optional[str] = None


class OpeMawbResponse(BaseModel):
    id: uuid.UUID
    operacion_id: uuid.UUID
    prefix: Optional[str]
    numero_mawb: str
    consignee_id: Optional[uuid.UUID]
    shipper_account: Optional[str]
    consignee_account: Optional[str]
    aerolinea_id: Optional[uuid.UUID]
    aeropuerto_origen_id: Optional[uuid.UUID]
    aeropuerto_destino_id: Optional[uuid.UUID]
    vuelo: Optional[str]
    fecha_vuelo: Optional[date]
    trm: Optional[Decimal]
    agent_iata_code: Optional[str]
    agent_account_no: Optional[str]
    tipo_pago_flete: str
    tipo_pago_otros: str
    moneda_flete: MonedaType
    valor_declarado_transporte: str
    valor_declarado_aduana: str
    monto_seguro: Optional[str]
    info_manejo: Optional[str]
    clase_tarifa: Optional[str]
    piezas: Optional[int]
    peso_bruto_kg: Optional[Decimal]
    peso_cargable_kg: Optional[Decimal]
    tarifa_por_kg: Optional[Decimal]
    descripcion_mercancia: Optional[str]
    dimensiones: Optional[str]
    flete_total: Optional[Decimal]
    fsc: Optional[Decimal]
    due_carrier: Optional[Decimal]
    cargo_valuacion: Optional[str]
    tax: Optional[str]
    otros_due_agent: Optional[Decimal]
    otros_due_carrier: Optional[Decimal]
    total_prepaid: Optional[Decimal]
    fecha_ejecucion: Optional[date]
    lugar_ejecucion: Optional[str]
    estado: EstadoDocTransporteType
    emitido_por: Optional[uuid.UUID] = None
    emitido_por_nombre: Optional[str] = None
    emitido_en: Optional[datetime] = None
    anulado_por: Optional[uuid.UUID] = None
    anulado_por_nombre: Optional[str] = None
    anulado_en: Optional[datetime] = None
    anulado_motivo: Optional[str] = None
    creado_en: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Manifiesto
# ---------------------------------------------------------------------------

class OpeManifiestoLineaCreate(BaseModel):
    hawb_id: uuid.UUID
    exportador_id: uuid.UUID
    importador_id: uuid.UUID
    piezas: Optional[int] = None
    peso_kg: Optional[Decimal] = None
    descripcion: Optional[str] = None


class OpeManifiestoLineaResponse(BaseModel):
    id: uuid.UUID
    manifiesto_id: uuid.UUID
    hawb_id: uuid.UUID
    exportador_id: uuid.UUID
    importador_id: uuid.UUID
    piezas: Optional[int]
    peso_kg: Optional[Decimal]
    descripcion: Optional[str]

    model_config = {"from_attributes": True}


class OpeManifiestoCreate(BaseModel):
    mawb_id: uuid.UUID
    aerolinea_id: Optional[uuid.UUID] = None
    fecha: date
    lineas: list[OpeManifiestoLineaCreate] = []


class OpeManifiestoUpdate(BaseModel):
    aerolinea_id: Optional[uuid.UUID] = None
    fecha: Optional[date] = None


class OpeAnularRequest(BaseModel):
    motivo: str


class OpeManifiestoResponse(BaseModel):
    id: uuid.UUID
    operacion_id: uuid.UUID
    mawb_id: uuid.UUID
    aerolinea_id: Optional[uuid.UUID]
    fecha: date
    estado: EstadoDocTransporteType
    emitido_por: Optional[uuid.UUID] = None
    emitido_por_nombre: Optional[str] = None
    emitido_en: Optional[datetime] = None
    anulado_por: Optional[uuid.UUID] = None
    anulado_por_nombre: Optional[str] = None
    anulado_en: Optional[datetime] = None
    anulado_motivo: Optional[str] = None
    creado_en: datetime
    lineas: list[OpeManifiestoLineaResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Evento (bitácora)
# ---------------------------------------------------------------------------

class OpeEventoCreate(BaseModel):
    tipo: TipoEventoType
    descripcion: str
    notificado_cliente: bool = False
    hawb_id: Optional[uuid.UUID] = None


class OpeEventoResponse(BaseModel):
    id: uuid.UUID
    operacion_id: uuid.UUID
    hawb_id: Optional[uuid.UUID] = None
    hawb_numero: Optional[str] = None
    fecha_hora: datetime
    usuario_id: uuid.UUID
    tipo: TipoEventoType
    descripcion: str
    notificado_cliente: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Documento requerido
# ---------------------------------------------------------------------------

class OpeDocumentoCreate(BaseModel):
    tipo: TipoDocumentoOpeType
    nombre: str


class OpeDocumentoUpdate(BaseModel):
    nombre: Optional[str] = None
    estado: Optional[EstadoDocOpeType] = None
    fecha_recepcion: Optional[date] = None
    archivo: Optional[str] = None


class OpeDocumentoResponse(BaseModel):
    id: uuid.UUID
    operacion_id: uuid.UUID
    tipo: TipoDocumentoOpeType
    nombre: str
    estado: EstadoDocOpeType
    fecha_recepcion: Optional[date]
    archivo: Optional[str]
    creado_en: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Carpeta completa de la operación (vista consolidada)
# ---------------------------------------------------------------------------

class OpeAprobarRequest(BaseModel):
    # None = crear operación nueva; con valor = asociar a esa operación ABIERTA.
    operacion_id: Optional[uuid.UUID] = None


class OpeOperacionCarpetaResponse(BaseModel):
    operacion: OpeOperacionResponse
    cotizaciones: list[OpeCotizacionResponse] = []
    clientes: list[ClienteResumen] = []
    hawbs: list[OpeHawbResponse] = []
    mawbs: list[OpeMawbResponse] = []
    manifiestos: list[OpeManifiestoResponse] = []
    eventos: list[OpeEventoResponse] = []
    documentos: list[OpeDocumentoResponse] = []
