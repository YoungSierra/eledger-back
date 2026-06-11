import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.consecutivos import ConsecutivoCreate, ConsecutivoUpdate, ConsecutivoResponse
from app.services import consecutivos_service

router = APIRouter(prefix="/consecutivos", tags=["Consecutivos"])


@router.get("", response_model=list[ConsecutivoResponse])
def listar(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return consecutivos_service.listar_consecutivos(db)


@router.post("", response_model=ConsecutivoResponse, status_code=201)
def crear(
    body: ConsecutivoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return consecutivos_service.crear_consecutivo(db, body, actor)


@router.put("/{id}", response_model=ConsecutivoResponse)
def actualizar(
    id: uuid.UUID,
    body: ConsecutivoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return consecutivos_service.actualizar_consecutivo(db, id, body, actor)


@router.delete("/{id}", status_code=204)
def eliminar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    consecutivos_service.eliminar_consecutivo(db, id)
