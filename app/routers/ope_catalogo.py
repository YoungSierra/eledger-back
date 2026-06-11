import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.ope import (
    OpeAerolineaCreate, OpeAerolineaResponse, OpeAerolineaUpdate,
    OpeAeropuertoCreate, OpeAeropuertoResponse, OpeAeropuertoUpdate,
    OpeConceptoCreate, OpeConceptoResponse, OpeConceptoUpdate,
)
from app.services import ope_catalogo_service

router = APIRouter(prefix="/operaciones", tags=["Operaciones — Catálogos"])


# ---------------------------------------------------------------------------
# Aerolíneas
# ---------------------------------------------------------------------------

@router.get("/aerolineas", response_model=list[OpeAerolineaResponse])
def listar_aerolineas(
    solo_activas: bool = Query(True),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.listar_aerolineas(db, solo_activas)


@router.post("/aerolineas", response_model=OpeAerolineaResponse, status_code=201)
def crear_aerolinea(
    body: OpeAerolineaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.crear_aerolinea(db, body, actor)


@router.get("/aerolineas/{aerolinea_id}", response_model=OpeAerolineaResponse)
def obtener_aerolinea(
    aerolinea_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.obtener_aerolinea(db, aerolinea_id)


@router.put("/aerolineas/{aerolinea_id}", response_model=OpeAerolineaResponse)
def actualizar_aerolinea(
    aerolinea_id: uuid.UUID,
    body: OpeAerolineaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.actualizar_aerolinea(db, aerolinea_id, body, actor)


# ---------------------------------------------------------------------------
# Aeropuertos
# ---------------------------------------------------------------------------

@router.get("/aeropuertos", response_model=list[OpeAeropuertoResponse])
def listar_aeropuertos(
    busqueda: Optional[str] = Query(None),
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.listar_aeropuertos(db, solo_activos, busqueda)


@router.post("/aeropuertos", response_model=OpeAeropuertoResponse, status_code=201)
def crear_aeropuerto(
    body: OpeAeropuertoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.crear_aeropuerto(db, body, actor)


@router.get("/aeropuertos/{aeropuerto_id}", response_model=OpeAeropuertoResponse)
def obtener_aeropuerto(
    aeropuerto_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.obtener_aeropuerto(db, aeropuerto_id)


@router.put("/aeropuertos/{aeropuerto_id}", response_model=OpeAeropuertoResponse)
def actualizar_aeropuerto(
    aeropuerto_id: uuid.UUID,
    body: OpeAeropuertoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.actualizar_aeropuerto(db, aeropuerto_id, body, actor)


# ---------------------------------------------------------------------------
# Conceptos tarifarios
# ---------------------------------------------------------------------------

@router.get("/conceptos", response_model=list[OpeConceptoResponse])
def listar_conceptos(
    seccion: Optional[str] = Query(None),
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.listar_conceptos(db, seccion, solo_activos)


@router.post("/conceptos", response_model=OpeConceptoResponse, status_code=201)
def crear_concepto(
    body: OpeConceptoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.crear_concepto(db, body, actor)


@router.get("/conceptos/{concepto_id}", response_model=OpeConceptoResponse)
def obtener_concepto(
    concepto_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.obtener_concepto(db, concepto_id)


@router.put("/conceptos/{concepto_id}", response_model=OpeConceptoResponse)
def actualizar_concepto(
    concepto_id: uuid.UUID,
    body: OpeConceptoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_catalogo_service.actualizar_concepto(db, concepto_id, body, actor)
