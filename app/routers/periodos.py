import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permisos import require_permission
from app.schemas.auth import UsuarioActual
from app.schemas.periodos import PeriodoCreate, PeriodoUpdate, PeriodoResponse
from app.services import periodo_service

router = APIRouter(prefix="/periodos", tags=["Períodos contables"])


@router.get("", response_model=list[PeriodoResponse])
def listar(
    anio: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "ver")),
):
    return periodo_service.listar_periodos(db, anio)


@router.post("", response_model=PeriodoResponse, status_code=201)
def crear(
    body: PeriodoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "crear")),
):
    return periodo_service.crear_periodo(db, body, actor)


@router.get("/{periodo_id}", response_model=PeriodoResponse)
def obtener(
    periodo_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "ver")),
):
    return periodo_service.obtener_periodo(db, periodo_id)


@router.put("/{periodo_id}", response_model=PeriodoResponse)
def actualizar(
    periodo_id: uuid.UUID,
    body: PeriodoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "editar")),
):
    return periodo_service.actualizar_periodo(db, periodo_id, body, actor)


@router.post("/{periodo_id}/reabrir", response_model=PeriodoResponse)
def reabrir(
    periodo_id: uuid.UUID,
    motivo: str,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "autorizar")),
):
    return periodo_service.reabrir_periodo(db, periodo_id, motivo, actor)


@router.post("/{periodo_id}/cerrar", response_model=PeriodoResponse)
def cerrar(
    periodo_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "autorizar")),
):
    return periodo_service.cerrar_periodo(db, periodo_id, actor)
