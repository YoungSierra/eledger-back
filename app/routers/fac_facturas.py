import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.facturacion import (
    FacFacturaCreate, FacFacturaUpdate, AnularFacturaRequest,
    FacFacturaResponse, FacListResponse,
)
from app.services import facturacion_service

router = APIRouter(prefix="/facturacion/facturas", tags=["Facturas de venta"])


@router.get("", response_model=FacListResponse)
def listar(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    estado: str | None = Query(None),
    dian_estado: str | None = Query(None),
    cliente_id: uuid.UUID | None = Query(None),
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.listar(db, pagina, por_pagina, estado, dian_estado, cliente_id, fecha_desde, fecha_hasta)


@router.post("", response_model=FacFacturaResponse, status_code=201)
def crear(
    body: FacFacturaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.crear(db, body, actor)


@router.get("/{id}", response_model=FacFacturaResponse)
def obtener(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.obtener(db, id)


@router.put("/{id}", response_model=FacFacturaResponse)
def actualizar(
    id: uuid.UUID,
    body: FacFacturaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.actualizar(db, id, body, actor)


@router.post("/{id}/contabilizar", response_model=FacFacturaResponse)
def contabilizar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.contabilizar(db, id, actor)


@router.post("/{id}/anular", response_model=FacFacturaResponse)
def anular(
    id: uuid.UUID,
    body: AnularFacturaRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.anular(db, id, body, actor)
