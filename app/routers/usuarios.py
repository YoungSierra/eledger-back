import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permisos import require_permission
from app.schemas.auth import UsuarioActual
from app.schemas.usuarios import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.services import usuario_service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("", response_model=list[UsuarioResponse])
def listar(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "ver")),
):
    return usuario_service.listar_usuarios(db, solo_activos)


@router.post("", response_model=UsuarioResponse, status_code=201)
def crear(
    body: UsuarioCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "crear")),
):
    return usuario_service.crear_usuario(db, body, actor)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def obtener(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "ver")),
):
    return usuario_service.obtener_usuario(db, usuario_id)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def actualizar(
    usuario_id: uuid.UUID,
    body: UsuarioUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "editar")),
):
    return usuario_service.actualizar_usuario(db, usuario_id, body, actor)


@router.delete("/{usuario_id}", status_code=204)
def desactivar(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "eliminar")),
):
    usuario_service.desactivar_usuario(db, usuario_id, actor)
