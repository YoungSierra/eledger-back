import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.asientos import (
    AsientoCreate, AsientoUpdate, AsientoCorregirRequest,
    AsientoResponse, AsientoListResponse,
    LineaCreate, LineaUpdate, LineaResponse,
)
from app.services import asientos_service

router = APIRouter(prefix="/asientos", tags=["Asientos contables"])


@router.get("", response_model=AsientoListResponse)
def listar(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    estado: Optional[str] = None,
    tipo_documento_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return asientos_service.listar(db, pagina, por_pagina, estado, tipo_documento_id, fecha_desde, fecha_hasta)


@router.post("", response_model=AsientoResponse, status_code=201)
def crear(
    body: AsientoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return asientos_service.crear(db, body, actor)


@router.get("/{id}", response_model=AsientoResponse)
def obtener(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return asientos_service.obtener(db, id)


@router.put("/{id}", response_model=AsientoResponse)
def actualizar(
    id: uuid.UUID,
    body: AsientoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return asientos_service.actualizar(db, id, body, actor)


@router.post("/{id}/lineas", response_model=LineaResponse, status_code=201)
def agregar_linea(
    id: uuid.UUID,
    body: LineaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return asientos_service.agregar_linea(db, id, body, actor)


@router.put("/{id}/lineas/{linea_id}", response_model=LineaResponse)
def actualizar_linea(
    id: uuid.UUID,
    linea_id: uuid.UUID,
    body: LineaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return asientos_service.actualizar_linea(db, id, linea_id, body, actor)


@router.delete("/{id}/lineas/{linea_id}", status_code=204)
def eliminar_linea(
    id: uuid.UUID,
    linea_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    asientos_service.eliminar_linea(db, id, linea_id, actor)


@router.post("/{id}/publicar", response_model=AsientoResponse)
def publicar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return asientos_service.publicar(db, id, actor)


@router.post("/{id}/corregir", response_model=AsientoResponse)
def corregir(
    id: uuid.UUID,
    body: AsientoCorregirRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return asientos_service.corregir(db, id, body, actor)
