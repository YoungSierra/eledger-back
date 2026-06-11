import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.maestros import (
    MonedaCreate, MonedaUpdate, MonedaResponse,
    CondicionPagoCreate, CondicionPagoUpdate, CondicionPagoResponse,
    TarifaIvaCreate, TarifaIvaUpdate, TarifaIvaResponse,
    RetencionCreate, RetencionUpdate, RetencionResponse,
)
from app.services import maestros_service

router = APIRouter(prefix="/maestros", tags=["Maestros financieros"])


@router.get("/monedas", response_model=list[MonedaResponse])
def listar_monedas(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.listar_monedas(db, solo_activas)


@router.post("/monedas", response_model=MonedaResponse, status_code=201)
def crear_moneda(
    body: MonedaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.crear_moneda(db, body, actor)


@router.put("/monedas/{id}", response_model=MonedaResponse)
def actualizar_moneda(
    id: uuid.UUID, body: MonedaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.actualizar_moneda(db, id, body, actor)


# ---------------------------------------------------------------------------
# Condiciones de pago
# ---------------------------------------------------------------------------

@router.get("/condiciones-pago", response_model=list[CondicionPagoResponse])
def listar_condiciones_pago(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.listar_condiciones_pago(db, solo_activas)


@router.post("/condiciones-pago", response_model=CondicionPagoResponse, status_code=201)
def crear_condicion_pago(
    body: CondicionPagoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.crear_condicion_pago(db, body, actor)


@router.put("/condiciones-pago/{id}", response_model=CondicionPagoResponse)
def actualizar_condicion_pago(
    id: uuid.UUID,
    body: CondicionPagoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.actualizar_condicion_pago(db, id, body, actor)


# ---------------------------------------------------------------------------
# Tarifas IVA
# ---------------------------------------------------------------------------

@router.get("/tarifas-iva", response_model=list[TarifaIvaResponse])
def listar_tarifas_iva(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.listar_tarifas_iva(db, solo_activas)


@router.post("/tarifas-iva", response_model=TarifaIvaResponse, status_code=201)
def crear_tarifa_iva(
    body: TarifaIvaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.crear_tarifa_iva(db, body, actor)


@router.put("/tarifas-iva/{id}", response_model=TarifaIvaResponse)
def actualizar_tarifa_iva(
    id: uuid.UUID,
    body: TarifaIvaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.actualizar_tarifa_iva(db, id, body, actor)


# ---------------------------------------------------------------------------
# Retenciones
# ---------------------------------------------------------------------------

@router.get("/retenciones", response_model=list[RetencionResponse])
def listar_retenciones(
    solo_activas: bool = Query(False),
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.listar_retenciones(db, solo_activas, tipo)


@router.post("/retenciones", response_model=RetencionResponse, status_code=201)
def crear_retencion(
    body: RetencionCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.crear_retencion(db, body, actor)


@router.put("/retenciones/{id}", response_model=RetencionResponse)
def actualizar_retencion(
    id: uuid.UUID,
    body: RetencionUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return maestros_service.actualizar_retencion(db, id, body, actor)
