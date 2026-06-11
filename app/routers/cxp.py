import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.cxp import (
    CxpDocumentoCreate, CxpDocumentoUpdate, AnularCxpRequest,
    CxpDocumentoResponse, CxpListResponse, CxpResumenResponse,
    ComprobanteCreate, FacturaPendienteCxpItem, AplicacionPendienteCxpItem,
)
from app.services import cxp_service

router = APIRouter(prefix="/cxp", tags=["CxP — Cuentas por pagar"])


@router.get("/facturas-pendientes", response_model=list[FacturaPendienteCxpItem])
def facturas_pendientes(
    tercero_id: uuid.UUID = Query(...),
    excluir_comprobante_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.facturas_pendientes_cxp(db, tercero_id, excluir_comprobante_id)


@router.post("/comprobante", response_model=CxpDocumentoResponse, status_code=201)
def crear_comprobante(
    body: ComprobanteCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.crear_comprobante(db, body, actor)


@router.get("/{id}/aplicaciones", response_model=list[AplicacionPendienteCxpItem])
def aplicaciones_comprobante(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.aplicaciones_comprobante(db, id)


@router.put("/{id}/comprobante", response_model=CxpDocumentoResponse)
def actualizar_comprobante(
    id: uuid.UUID,
    body: ComprobanteCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.actualizar_comprobante(db, id, body, actor)


@router.get("/resumen", response_model=CxpResumenResponse)
def resumen(
    fecha_corte: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.resumen(db, fecha_corte)


@router.get("/resumen/excel")
def resumen_excel(
    fecha_corte: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.resumen_excel(db, fecha_corte)


@router.get("", response_model=CxpListResponse)
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
    return cxp_service.listar(db, pagina, por_pagina, tipo, estado, tercero_id, fecha_desde, fecha_hasta, solo_pendientes)


@router.post("", response_model=CxpDocumentoResponse, status_code=201)
def crear(
    body: CxpDocumentoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.crear(db, body, actor)


@router.get("/{id}", response_model=CxpDocumentoResponse)
def obtener(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.obtener(db, id)


@router.put("/{id}", response_model=CxpDocumentoResponse)
def actualizar(
    id: uuid.UUID,
    body: CxpDocumentoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.actualizar(db, id, body, actor)


@router.post("/{id}/contabilizar", response_model=CxpDocumentoResponse)
def contabilizar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.contabilizar(db, id, actor)


@router.post("/{id}/anular", response_model=CxpDocumentoResponse)
def anular(
    id: uuid.UUID,
    body: AnularCxpRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return cxp_service.anular(db, id, body, actor)
