import uuid
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.ope import (
    OpeOperacionResponse, OpeOperacionUpdate, OpeOperacionCarpetaResponse,
    OpeHawbCreate, OpeHawbResponse, OpeHawbUpdate,
    OpeMawbCreate, OpeMawbResponse, OpeMawbUpdate,
    OpeManifiestoCreate, OpeManifiestoResponse, OpeManifiestoUpdate,
    OpeEventoCreate, OpeEventoResponse,
    OpeDocumentoCreate, OpeDocumentoResponse, OpeDocumentoUpdate,
)
from app.services import ope_operacion_service

router = APIRouter(prefix="/operaciones/operaciones", tags=["Operaciones — Carpeta"])


# ---------------------------------------------------------------------------
# Operación
# ---------------------------------------------------------------------------

@router.get("", response_model=list[OpeOperacionResponse])
def listar(
    estado: Optional[str] = Query(None, description="ABIERTA, EN_CURSO, CERRADA, CANCELADA"),
    busqueda: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.listar_operaciones(db, actor, estado, busqueda, fecha_desde, fecha_hasta)


@router.get("/{operacion_id}", response_model=OpeOperacionResponse)
def obtener(
    operacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.obtener_operacion(db, operacion_id)


@router.put("/{operacion_id}", response_model=OpeOperacionResponse)
def actualizar(
    operacion_id: uuid.UUID,
    body: OpeOperacionUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.actualizar_operacion(db, operacion_id, body, actor)


@router.get("/{operacion_id}/carpeta", response_model=OpeOperacionCarpetaResponse)
def carpeta(
    operacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Vista consolidada con cotización, HAWB, MAWB, manifiesto, eventos y documentos."""
    return ope_operacion_service.obtener_carpeta(db, operacion_id)


# ---------------------------------------------------------------------------
# HAWB
# ---------------------------------------------------------------------------

@router.get("/{operacion_id}/hawbs", response_model=list[OpeHawbResponse])
def listar_hawbs(
    operacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.listar_hawbs(db, operacion_id)


@router.post("/{operacion_id}/hawbs", response_model=OpeHawbResponse, status_code=201)
def crear_hawb(
    operacion_id: uuid.UUID,
    body: OpeHawbCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.crear_hawb(db, operacion_id, body, actor)


@router.get("/{operacion_id}/hawbs/{hawb_id}", response_model=OpeHawbResponse)
def obtener_hawb(
    operacion_id: uuid.UUID,
    hawb_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.obtener_hawb(db, operacion_id, hawb_id)


@router.put("/{operacion_id}/hawbs/{hawb_id}", response_model=OpeHawbResponse)
def actualizar_hawb(
    operacion_id: uuid.UUID,
    hawb_id: uuid.UUID,
    body: OpeHawbUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.actualizar_hawb(db, operacion_id, hawb_id, body, actor)


# ---------------------------------------------------------------------------
# MAWB
# ---------------------------------------------------------------------------

@router.get("/{operacion_id}/mawbs", response_model=list[OpeMawbResponse])
def listar_mawbs(
    operacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.listar_mawbs(db, operacion_id)


@router.post("/{operacion_id}/mawbs", response_model=OpeMawbResponse, status_code=201)
def crear_mawb(
    operacion_id: uuid.UUID,
    body: OpeMawbCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.crear_mawb(db, operacion_id, body, actor)


@router.get("/{operacion_id}/mawbs/{mawb_id}", response_model=OpeMawbResponse)
def obtener_mawb(
    operacion_id: uuid.UUID,
    mawb_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.obtener_mawb(db, operacion_id, mawb_id)


@router.put("/{operacion_id}/mawbs/{mawb_id}", response_model=OpeMawbResponse)
def actualizar_mawb(
    operacion_id: uuid.UUID,
    mawb_id: uuid.UUID,
    body: OpeMawbUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.actualizar_mawb(db, operacion_id, mawb_id, body, actor)


# ---------------------------------------------------------------------------
# Manifiesto
# ---------------------------------------------------------------------------

@router.get("/{operacion_id}/manifiestos", response_model=list[OpeManifiestoResponse])
def listar_manifiestos(
    operacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.listar_manifiestos(db, operacion_id)


@router.get("/{operacion_id}/manifiestos/{manifiesto_id}", response_model=OpeManifiestoResponse)
def obtener_manifiesto(
    operacion_id: uuid.UUID,
    manifiesto_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.obtener_manifiesto(db, operacion_id, manifiesto_id)


@router.post("/{operacion_id}/manifiestos", response_model=OpeManifiestoResponse, status_code=201)
def crear_manifiesto(
    operacion_id: uuid.UUID,
    body: OpeManifiestoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.crear_manifiesto(db, operacion_id, body, actor)


@router.put("/{operacion_id}/manifiestos/{manifiesto_id}", response_model=OpeManifiestoResponse)
def actualizar_manifiesto(
    operacion_id: uuid.UUID,
    manifiesto_id: uuid.UUID,
    body: OpeManifiestoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.actualizar_manifiesto(db, operacion_id, manifiesto_id, body, actor)


# ---------------------------------------------------------------------------
# Eventos (bitácora)
# ---------------------------------------------------------------------------

@router.get("/{operacion_id}/eventos", response_model=list[OpeEventoResponse])
def listar_eventos(
    operacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.listar_eventos(db, operacion_id)


@router.post("/{operacion_id}/eventos", response_model=OpeEventoResponse, status_code=201)
def registrar_evento(
    operacion_id: uuid.UUID,
    body: OpeEventoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.registrar_evento(db, operacion_id, body, actor)


# ---------------------------------------------------------------------------
# Documentos requeridos
# ---------------------------------------------------------------------------

@router.get("/{operacion_id}/documentos", response_model=list[OpeDocumentoResponse])
def listar_documentos(
    operacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.listar_documentos(db, operacion_id)


@router.post("/{operacion_id}/documentos", response_model=OpeDocumentoResponse, status_code=201)
def crear_documento(
    operacion_id: uuid.UUID,
    body: OpeDocumentoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.crear_documento(db, operacion_id, body, actor)


@router.put("/{operacion_id}/documentos/{documento_id}", response_model=OpeDocumentoResponse)
def actualizar_documento(
    operacion_id: uuid.UUID,
    documento_id: uuid.UUID,
    body: OpeDocumentoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.actualizar_documento(db, operacion_id, documento_id, body, actor)


@router.post("/{operacion_id}/documentos/{documento_id}/archivo", response_model=OpeDocumentoResponse)
def subir_archivo(
    operacion_id: uuid.UUID,
    documento_id: uuid.UUID,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    from app.core.config import settings
    # Validar extensión
    ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls", ".doc", ".docx"}
    suffix = Path(archivo.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: {suffix}")
    return ope_operacion_service.subir_archivo(
        db, operacion_id, documento_id, archivo, settings.upload_path, actor
    )


@router.get("/{operacion_id}/documentos/{documento_id}/archivo")
def descargar_archivo(
    operacion_id: uuid.UUID,
    documento_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return ope_operacion_service.descargar_archivo(db, operacion_id, documento_id)
