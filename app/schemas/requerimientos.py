import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

EstadoReq = Literal["PENDIENTE", "EN_PROCESO", "REVISION", "REALIZADO"]
PrioridadReq = Literal["BAJA", "MEDIA", "ALTA"]


class RequerimientoCreate(BaseModel):
    asunto: str
    descripcion: str
    asignado_id: uuid.UUID
    prioridad: PrioridadReq = "MEDIA"
    fecha_limite: Optional[date] = None


class RequerimientoEstadoRequest(BaseModel):
    estado: EstadoReq


class MensajeCreate(BaseModel):
    cuerpo: str


class MensajeResponse(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID
    usuario_nombre: Optional[str] = None
    tipo: str
    cuerpo: str
    estado_nuevo: Optional[str] = None
    creado_en: datetime

    model_config = {"from_attributes": True}


class RequerimientoListItem(BaseModel):
    id: uuid.UUID
    numero: str
    asunto: str
    estado: EstadoReq
    prioridad: PrioridadReq
    fecha_limite: Optional[date] = None
    solicitante_id: uuid.UUID
    solicitante_nombre: Optional[str] = None
    asignado_id: uuid.UUID
    asignado_nombre: Optional[str] = None
    tiene_adjunto: bool = False
    creado_en: datetime

    model_config = {"from_attributes": True}


class RequerimientoResponse(RequerimientoListItem):
    descripcion: str
    archivo_nombre: Optional[str] = None
    mensajes: list[MensajeResponse] = []


class RequerimientoListResponse(BaseModel):
    items: list[RequerimientoListItem]
    total: int
    pagina: int
    por_pagina: int


class UsuarioSeleccion(BaseModel):
    id: uuid.UUID
    nombre: str
    email: Optional[str] = None

    model_config = {"from_attributes": True}
