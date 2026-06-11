import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.terceros import TerceroCreate, TerceroResponse, TerceroSummary, TerceroUpdate
from app.services import tercero_service

router = APIRouter(prefix="/terceros", tags=["Terceros"])


@router.get("", response_model=list[TerceroSummary])
def listar(
    tipo_tercero: Optional[str] = Query(None, description="CLIENTE, PROVEEDOR, EMPLEADO, OTRO"),
    busqueda: Optional[str] = Query(None),
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return tercero_service.listar_terceros(db, tipo_tercero, busqueda, solo_activos)


@router.post("", response_model=TerceroResponse, status_code=201)
def crear(
    body: TerceroCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return tercero_service.crear_tercero(db, body, actor)


@router.get("/{tercero_id}", response_model=TerceroResponse)
def obtener(
    tercero_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return tercero_service.obtener_tercero(db, tercero_id)


@router.put("/{tercero_id}", response_model=TerceroResponse)
def actualizar(
    tercero_id: uuid.UUID,
    body: TerceroUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return tercero_service.actualizar_tercero(db, tercero_id, body, actor)
