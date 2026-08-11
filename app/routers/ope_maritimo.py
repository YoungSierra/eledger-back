import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.ope_maritimo import (
    AnularHblRequest,
    ContenedorCreate, ContenedorResponse, ContenedorUpdate,
    HblCreate, HblResponse, HblUpdate,
    MaritimoBusquedaItem, MaritimoCarpetaResponse,
    MblCreate, MblResponse, MblUpdate,
)
from app.services import ope_maritimo_service as svc

router = APIRouter(prefix="/operaciones", tags=["Operaciones — Marítimo"])


# ---------------------------------------------------------------------------
# Búsqueda / tracking — va primero para que no la capture /{operacion_id}
# ---------------------------------------------------------------------------

@router.get("/maritimo/buscar", response_model=list[MaritimoBusquedaItem])
def buscar(
    q: str = Query(..., min_length=2, description="Número de BL, booking o contenedor"),
    limite: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Rastreo por número de BL, booking o contenedor."""
    return svc.buscar(db, q, limite)


# ---------------------------------------------------------------------------
# Carpeta marítima de una operación
# ---------------------------------------------------------------------------

@router.get("/operaciones/{operacion_id}/maritimo", response_model=MaritimoCarpetaResponse)
def carpeta(
    operacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.obtener_carpeta(db, operacion_id)


# ── MBL ────────────────────────────────────────────────────────────────────

@router.post("/operaciones/{operacion_id}/mbl", response_model=MblResponse, status_code=201)
def crear_mbl(
    operacion_id: uuid.UUID, body: MblCreate,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return svc.crear_mbl(db, operacion_id, body, actor)


@router.put("/operaciones/{operacion_id}/mbl/{mbl_id}", response_model=MblResponse)
def actualizar_mbl(
    operacion_id: uuid.UUID, mbl_id: uuid.UUID, body: MblUpdate,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return svc.actualizar_mbl(db, operacion_id, mbl_id, body, actor)


@router.delete("/operaciones/{operacion_id}/mbl/{mbl_id}", status_code=204)
def eliminar_mbl(
    operacion_id: uuid.UUID, mbl_id: uuid.UUID,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    svc.eliminar_mbl(db, operacion_id, mbl_id, actor)


# ── Contenedores ───────────────────────────────────────────────────────────

@router.post("/operaciones/{operacion_id}/contenedores", response_model=ContenedorResponse, status_code=201)
def crear_contenedor(
    operacion_id: uuid.UUID, body: ContenedorCreate,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return svc.crear_contenedor(db, operacion_id, body, actor)


@router.put("/operaciones/{operacion_id}/contenedores/{cont_id}", response_model=ContenedorResponse)
def actualizar_contenedor(
    operacion_id: uuid.UUID, cont_id: uuid.UUID, body: ContenedorUpdate,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return svc.actualizar_contenedor(db, operacion_id, cont_id, body, actor)


@router.delete("/operaciones/{operacion_id}/contenedores/{cont_id}", status_code=204)
def eliminar_contenedor(
    operacion_id: uuid.UUID, cont_id: uuid.UUID,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    svc.eliminar_contenedor(db, operacion_id, cont_id, actor)


# ── HBL ────────────────────────────────────────────────────────────────────

@router.post("/operaciones/{operacion_id}/hbl", response_model=HblResponse, status_code=201)
def crear_hbl(
    operacion_id: uuid.UUID, body: HblCreate,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return svc.crear_hbl(db, operacion_id, body, actor)


@router.put("/operaciones/{operacion_id}/hbl/{hbl_id}", response_model=HblResponse)
def actualizar_hbl(
    operacion_id: uuid.UUID, hbl_id: uuid.UUID, body: HblUpdate,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return svc.actualizar_hbl(db, operacion_id, hbl_id, body, actor)


@router.post("/operaciones/{operacion_id}/hbl/{hbl_id}/emitir", response_model=HblResponse)
def emitir_hbl(
    operacion_id: uuid.UUID, hbl_id: uuid.UUID,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return svc.emitir_hbl(db, operacion_id, hbl_id, actor)


@router.post("/operaciones/{operacion_id}/hbl/{hbl_id}/anular", response_model=HblResponse)
def anular_hbl(
    operacion_id: uuid.UUID, hbl_id: uuid.UUID, body: AnularHblRequest,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return svc.anular_hbl(db, operacion_id, hbl_id, body.motivo, actor)


@router.delete("/operaciones/{operacion_id}/hbl/{hbl_id}", status_code=204)
def eliminar_hbl(
    operacion_id: uuid.UUID, hbl_id: uuid.UUID,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    svc.eliminar_hbl(db, operacion_id, hbl_id, actor)
