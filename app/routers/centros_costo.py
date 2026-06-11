import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permisos import require_permission
from app.schemas.auth import UsuarioActual
from app.schemas.centros_costo import CentroCostoCreate, CentroCostoResponse, CentroCostoUpdate
from app.services import centro_costo_service

router = APIRouter(prefix="/centros-costo", tags=["Centros de costo"])


@router.get("", response_model=list[CentroCostoResponse])
def listar(
    padre_id: Optional[uuid.UUID] = Query(None),
    busqueda: Optional[str] = Query(None),
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "ver")),
):
    return centro_costo_service.listar(db, padre_id, solo_activos, busqueda)


@router.post("", response_model=CentroCostoResponse, status_code=201)
def crear(
    body: CentroCostoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "crear")),
):
    return centro_costo_service.crear(db, body, actor)


@router.get("/{centro_id}", response_model=CentroCostoResponse)
def obtener(
    centro_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "ver")),
):
    return centro_costo_service.obtener(db, centro_id)


@router.put("/{centro_id}", response_model=CentroCostoResponse)
def actualizar(
    centro_id: uuid.UUID,
    body: CentroCostoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "editar")),
):
    return centro_costo_service.actualizar(db, centro_id, body, actor)


@router.post("/{centro_id}/reactivar", response_model=CentroCostoResponse)
def reactivar(
    centro_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "editar")),
):
    return centro_costo_service.reactivar(db, centro_id, actor)


@router.delete("/{centro_id}", status_code=204)
def desactivar(
    centro_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "eliminar")),
):
    centro_costo_service.desactivar(db, centro_id, actor)
