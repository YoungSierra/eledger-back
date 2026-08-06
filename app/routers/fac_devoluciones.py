import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.devoluciones import (
    DevolucionCreate, DevolucionUpdate, AnularDevolucionRequest,
    DevolucionResponse, DevolucionListResponse, DevPreviewResponse,
)
from app.services import devoluciones_service

router = APIRouter(prefix="/facturacion/devoluciones", tags=["Devoluciones en ventas"])


@router.get("", response_model=DevolucionListResponse)
def listar(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    estado: str | None = Query(None),
    factura_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.listar(db, pagina, por_pagina, estado, factura_id)


@router.post("/preview-asiento", response_model=DevPreviewResponse)
def preview_asiento_nuevo(
    body: DevolucionCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.preview_asiento_nuevo(db, body)


@router.post("", response_model=DevolucionResponse, status_code=201)
def crear(
    body: DevolucionCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.crear(db, body, actor)


@router.get("/{id}", response_model=DevolucionResponse)
def obtener(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.obtener(db, id)


@router.put("/{id}", response_model=DevolucionResponse)
def actualizar(
    id: uuid.UUID,
    body: DevolucionUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.actualizar(db, id, body, actor)


@router.delete("/{id}", status_code=204)
def eliminar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    devoluciones_service.eliminar(db, id, actor)


@router.get("/{id}/preview-asiento", response_model=DevPreviewResponse)
def preview_asiento(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.preview_asiento(db, id)


@router.get("/{id}/asiento", response_model=DevPreviewResponse)
def asiento_contabilizado(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.asiento_contabilizado(db, id)


@router.post("/{id}/contabilizar", response_model=DevolucionResponse)
def contabilizar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.contabilizar(db, id, actor)


@router.post("/{id}/anular", response_model=DevolucionResponse)
def anular(
    id: uuid.UUID,
    body: AnularDevolucionRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return devoluciones_service.anular(db, id, body, actor)
