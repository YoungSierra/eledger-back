import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.resoluciones import ResolucionCreate, ResolucionUpdate, ResolucionResponse
from app.services import resoluciones_service

router = APIRouter(prefix="/facturacion/resoluciones", tags=["Resoluciones DIAN"])


@router.get("/activa", response_model=ResolucionResponse | None)
def activa(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return resoluciones_service.obtener_activa(db)


@router.get("", response_model=list[ResolucionResponse])
def listar(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return resoluciones_service.listar(db, solo_activas)


@router.post("", response_model=ResolucionResponse, status_code=201)
def crear(
    body: ResolucionCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return resoluciones_service.crear(db, body, actor)


@router.put("/{id}", response_model=ResolucionResponse)
def actualizar(
    id: uuid.UUID, body: ResolucionUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return resoluciones_service.actualizar(db, id, body, actor)
