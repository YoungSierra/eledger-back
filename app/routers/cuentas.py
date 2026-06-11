import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permisos import require_permission
from app.schemas.auth import UsuarioActual
from app.schemas.cuentas import CuentaCreate, CuentaResponse, CuentaUpdate
from app.services import cuenta_service

router = APIRouter(prefix="/cuentas", tags=["Plan de cuentas"])


@router.get("", response_model=list[CuentaResponse])
def listar(
    padre_id: Optional[uuid.UUID] = Query(None),
    busqueda: Optional[str] = Query(None),
    solo_activas: bool = Query(True),
    solo_movimiento: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "ver")),
):
    return cuenta_service.listar_cuentas(db, padre_id, solo_activas, busqueda, solo_movimiento)


@router.post("", response_model=CuentaResponse, status_code=201)
def crear(
    body: CuentaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "crear")),
):
    return cuenta_service.crear_cuenta(db, body, actor)


@router.get("/{cuenta_id}", response_model=CuentaResponse)
def obtener(
    cuenta_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "ver")),
):
    return cuenta_service.obtener_cuenta(db, cuenta_id)


@router.put("/{cuenta_id}", response_model=CuentaResponse)
def actualizar(
    cuenta_id: uuid.UUID,
    body: CuentaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "editar")),
):
    return cuenta_service.actualizar_cuenta(db, cuenta_id, body, actor)


@router.post("/{cuenta_id}/reactivar", response_model=CuentaResponse)
def reactivar(
    cuenta_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "editar")),
):
    return cuenta_service.reactivar_cuenta(db, cuenta_id, actor)


@router.delete("/{cuenta_id}", status_code=204)
def desactivar(
    cuenta_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("contabilidad", "eliminar")),
):
    cuenta_service.desactivar_cuenta(db, cuenta_id, actor)
