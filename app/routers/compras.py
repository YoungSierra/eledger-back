import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.permisos import require_permission
from app.schemas.auth import UsuarioActual
from app.schemas.compras import (
    OcCreate, OcUpdate, OcResponse, OcListResponse,
    RecepcionCreate, RecepcionUpdate, RecepcionResponse, RecepcionListResponse,
)
from app.services import compras_service as svc

router = APIRouter(prefix="/compras", tags=["Compras"])


# ─── Órdenes de compra ───────────────────────────────────────────────────────

@router.get("/ordenes", response_model=OcListResponse)
def listar_ocs(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    estado: Optional[List[str]] = Query(None),
    proveedor_id: Optional[uuid.UUID] = Query(None),
    busqueda: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.listar_ocs(db, pagina, por_pagina, estado, proveedor_id, busqueda)


@router.post("/ordenes", response_model=OcResponse, status_code=201)
def crear_oc(data: OcCreate, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return svc.crear_oc(db, data, actor)


@router.get("/ordenes/{oc_id}", response_model=OcResponse)
def obtener_oc(oc_id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return svc.obtener_oc(db, oc_id)


@router.put("/ordenes/{oc_id}", response_model=OcResponse)
def actualizar_oc(oc_id: uuid.UUID, data: OcUpdate, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return svc.actualizar_oc(db, oc_id, data, actor)


@router.post("/ordenes/{oc_id}/aprobar", response_model=OcResponse)
def aprobar_oc(
    oc_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("compras", "autorizar")),
):
    return svc.aprobar_oc(db, oc_id, actor)


@router.post("/ordenes/{oc_id}/anular", response_model=OcResponse)
def anular_oc(
    oc_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("compras", "eliminar")),
):
    return svc.anular_oc(db, oc_id, actor)


# ─── Recepciones ─────────────────────────────────────────────────────────────

@router.get("/recepciones", response_model=RecepcionListResponse)
def listar_recepciones(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    estado: Optional[str] = Query(None),
    oc_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.listar_recepciones(db, pagina, por_pagina, estado, oc_id)


@router.post("/recepciones", response_model=RecepcionResponse, status_code=201)
def crear_recepcion(data: RecepcionCreate, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return svc.crear_recepcion(db, data, actor)


@router.get("/recepciones/{rec_id}", response_model=RecepcionResponse)
def obtener_recepcion(rec_id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return svc.obtener_recepcion(db, rec_id)


@router.put("/recepciones/{rec_id}", response_model=RecepcionResponse)
def actualizar_recepcion(rec_id: uuid.UUID, data: RecepcionUpdate, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return svc.actualizar_recepcion(db, rec_id, data, actor)


@router.post("/recepciones/{rec_id}/confirmar", response_model=RecepcionResponse)
def confirmar_recepcion(rec_id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return svc.confirmar_recepcion(db, rec_id, actor)


@router.post("/recepciones/{rec_id}/anular", response_model=RecepcionResponse)
def anular_recepcion(rec_id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return svc.anular_recepcion(db, rec_id, actor)
