import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.ope import (
    OpeCotizacionCreate, OpeCotizacionResponse, OpeCotizacionSummary, OpeCotizacionUpdate,
    OpeCotizacionLineaCreate, OpeCotizacionLineaResponse, OpeCotizacionLineaUpdate,
    OpeCotizacionMargenResponse,
    OpeOperacionResponse,
    OpeAprobarRequest,
)
from app.services import ope_cotizacion_service, ope_operacion_service

router = APIRouter(prefix="/operaciones/cotizaciones", tags=["Operaciones — Cotizaciones"])


@router.get("", response_model=list[OpeCotizacionSummary])
def listar(
    estado: Optional[str] = Query(None, description="BORRADOR, ENVIADA, APROBADA, RECHAZADA, VENCIDA"),
    cliente_id: Optional[uuid.UUID] = Query(None),
    busqueda: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.listar_cotizaciones(db, actor, estado, cliente_id, busqueda, fecha_desde, fecha_hasta)


@router.post("", response_model=OpeCotizacionResponse, status_code=201)
def crear(
    body: OpeCotizacionCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.crear_cotizacion(db, body, actor)


@router.get("/{cotizacion_id}", response_model=OpeCotizacionResponse)
def obtener(
    cotizacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.obtener_cotizacion(db, cotizacion_id)


@router.put("/{cotizacion_id}", response_model=OpeCotizacionResponse)
def actualizar(
    cotizacion_id: uuid.UUID,
    body: OpeCotizacionUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.actualizar_cotizacion(db, cotizacion_id, body, actor)


# ---------------------------------------------------------------------------
# Líneas
# ---------------------------------------------------------------------------

@router.post("/{cotizacion_id}/lineas", response_model=OpeCotizacionLineaResponse, status_code=201)
def agregar_linea(
    cotizacion_id: uuid.UUID,
    body: OpeCotizacionLineaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.agregar_linea(db, cotizacion_id, body, actor)


@router.put("/{cotizacion_id}/lineas/{linea_id}", response_model=OpeCotizacionLineaResponse)
def actualizar_linea(
    cotizacion_id: uuid.UUID,
    linea_id: uuid.UUID,
    body: OpeCotizacionLineaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.actualizar_linea(db, cotizacion_id, linea_id, body, actor)


@router.delete("/{cotizacion_id}/lineas/{linea_id}", status_code=204)
def eliminar_linea(
    cotizacion_id: uuid.UUID,
    linea_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    ope_cotizacion_service.eliminar_linea(db, cotizacion_id, linea_id, actor)


# ---------------------------------------------------------------------------
# Transiciones de estado
# ---------------------------------------------------------------------------

@router.post("/{cotizacion_id}/enviar", response_model=OpeCotizacionResponse)
def enviar(
    cotizacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.enviar_cotizacion(db, cotizacion_id, actor)


@router.post("/{cotizacion_id}/aprobar", response_model=OpeOperacionResponse)
def aprobar(
    cotizacion_id: uuid.UUID,
    body: OpeAprobarRequest = OpeAprobarRequest(),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Aprueba la cotización. Sin operacion_id crea una operación nueva; con
    operacion_id la asocia a una operación ABIERTA existente (consolidación)."""
    return ope_cotizacion_service.aprobar_cotizacion(db, cotizacion_id, actor, body.operacion_id)


@router.post("/{cotizacion_id}/rechazar", response_model=OpeCotizacionResponse)
def rechazar(
    cotizacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.rechazar_cotizacion(db, cotizacion_id, actor)


@router.post("/{cotizacion_id}/reabrir", response_model=OpeCotizacionResponse)
def reabrir(
    cotizacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Devuelve la cotización a BORRADOR para permitir ajustes."""
    return ope_cotizacion_service.reabrir_cotizacion(db, cotizacion_id, actor)


# ---------------------------------------------------------------------------
# Margen
# ---------------------------------------------------------------------------

@router.get("/{cotizacion_id}/operacion", response_model=OpeOperacionResponse)
def operacion_de_cotizacion(
    cotizacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Retorna la operación creada al aprobar esta cotización."""
    return ope_operacion_service.obtener_operacion_por_cotizacion(db, cotizacion_id)


@router.get("/{cotizacion_id}/margen", response_model=OpeCotizacionMargenResponse)
def margen(
    cotizacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_cotizacion_service.calcular_margen(db, cotizacion_id)
