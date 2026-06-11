import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.cxc import (
    CxcDocumentoCreate, CxcDocumentoUpdate, AnularRequest, AplicarRequest,
    CxcDocumentoResponse, CxcListResponse, CxcResumenResponse,
    ReciboCreate, FacturaPendienteItem, AplicacionPendienteItem,
)
from app.services import cxc_service

router = APIRouter(prefix="/cxc", tags=["CxC — Cuentas por cobrar"])


@router.get("/facturas-pendientes", response_model=list[FacturaPendienteItem])
def facturas_pendientes(
    tercero_id: uuid.UUID = Query(...),
    excluir_recibo_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.facturas_pendientes(db, tercero_id, excluir_recibo_id)


@router.post("/recibo", response_model=CxcDocumentoResponse, status_code=201)
def crear_recibo(
    body: ReciboCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.crear_recibo(db, body, actor)


@router.get("/{id}/aplicaciones-pendientes", response_model=list[AplicacionPendienteItem])
def aplicaciones_pendientes(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.aplicaciones_pendientes(db, id)


@router.put("/{id}/recibo", response_model=CxcDocumentoResponse)
def actualizar_recibo(
    id: uuid.UUID,
    body: ReciboCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.actualizar_recibo(db, id, body, actor)


@router.get("/resumen", response_model=CxcResumenResponse)
def resumen(
    fecha_corte: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.resumen(db, fecha_corte)


@router.get("/resumen/excel")
def resumen_excel(
    fecha_corte: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.resumen_excel(db, fecha_corte)


@router.get("", response_model=CxcListResponse)
def listar(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    tercero_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    solo_pendientes: bool = False,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.listar(db, pagina, por_pagina, tipo, estado, tercero_id, fecha_desde, fecha_hasta, solo_pendientes)


@router.post("", response_model=CxcDocumentoResponse, status_code=201)
def crear(
    body: CxcDocumentoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.crear(db, body, actor)


@router.get("/{id}", response_model=CxcDocumentoResponse)
def obtener(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.obtener(db, id)


@router.put("/{id}", response_model=CxcDocumentoResponse)
def actualizar(
    id: uuid.UUID,
    body: CxcDocumentoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.actualizar(db, id, body, actor)


@router.post("/{id}/contabilizar", response_model=CxcDocumentoResponse)
def contabilizar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.contabilizar(db, id, actor)


@router.post("/{id}/anular", response_model=CxcDocumentoResponse)
def anular(
    id: uuid.UUID,
    body: AnularRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.anular(db, id, body, actor)


@router.post("/aplicar", status_code=200)
def aplicar(
    body: AplicarRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxc_service.aplicar(db, body, actor)
