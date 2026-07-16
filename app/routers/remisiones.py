import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.remisiones import RemisionCreate, RemisionDetalle, RemisionListResponse
from app.services import remisiones_service

router = APIRouter(prefix="/inventario/remisiones", tags=["Remisiones"])


@router.get("", response_model=RemisionListResponse)
def listar_remisiones(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(30, ge=1, le=100),
    estado: Optional[str] = Query(None),
    cliente_id: Optional[uuid.UUID] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    sin_facturar: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return remisiones_service.listar_remisiones(db, pagina, por_pagina, estado, cliente_id, fecha_desde, fecha_hasta, sin_facturar)


@router.get("/{remision_id}", response_model=RemisionDetalle)
def obtener_remision(
    remision_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return remisiones_service.obtener_remision(db, remision_id)


@router.post("", response_model=RemisionDetalle, status_code=201)
def crear_remision(
    data: RemisionCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return remisiones_service.crear_remision(db, data, actor)


@router.put("/{remision_id}", response_model=RemisionDetalle)
def editar_remision(
    remision_id: uuid.UUID,
    data: RemisionCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return remisiones_service.editar_remision(db, remision_id, data, actor)


@router.post("/{remision_id}/despachar", response_model=RemisionDetalle)
def despachar_remision(
    remision_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return remisiones_service.despachar_remision(db, remision_id, actor)
