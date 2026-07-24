import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.requerimientos import (
    RequerimientoCreate, RequerimientoEstadoRequest, MensajeCreate,
    RequerimientoResponse, RequerimientoListResponse, UsuarioSeleccion,
)
from app.services import requerimientos_service as svc

router = APIRouter(prefix="/requerimientos", tags=["Requerimientos"])


@router.get("/usuarios", response_model=list[UsuarioSeleccion])
def usuarios_seleccionables(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.listar_usuarios_seleccionables(db)


@router.get("", response_model=RequerimientoListResponse)
def listar(
    buzon: str = Query("recibidos", description="recibidos | enviados"),
    estado: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
    remitente_id: Optional[uuid.UUID] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    no_finalizados: bool = Query(False),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.listar(db, actor, buzon, estado, prioridad, remitente_id,
                      fecha_desde, fecha_hasta, no_finalizados, pagina, por_pagina)


@router.get("/pendientes-count")
def pendientes_count(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return {"count": svc.pendientes_count(db, actor)}


@router.post("", response_model=RequerimientoResponse, status_code=201)
def crear(
    body: RequerimientoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.crear(db, body, actor)


@router.get("/{req_id}", response_model=RequerimientoResponse)
def obtener(
    req_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.obtener_detalle(db, req_id)


@router.post("/{req_id}/estado", response_model=RequerimientoResponse)
def cambiar_estado(
    req_id: uuid.UUID,
    body: RequerimientoEstadoRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.cambiar_estado(db, req_id, body, actor)


@router.post("/{req_id}/mensajes", response_model=RequerimientoResponse)
def agregar_mensaje(
    req_id: uuid.UUID,
    body: MensajeCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.agregar_mensaje(db, req_id, body, actor)


@router.post("/{req_id}/adjunto", response_model=RequerimientoResponse)
def subir_adjunto(
    req_id: uuid.UUID,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.subir_adjunto(db, req_id, archivo, actor)


@router.get("/{req_id}/adjunto")
def descargar_adjunto(
    req_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
) -> FileResponse:
    return svc.descargar_adjunto(db, req_id)
