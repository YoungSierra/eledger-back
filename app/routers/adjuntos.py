import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core import almacenamiento
from app.models.adjuntos import AdmAdjunto
from app.models.admin import AdmUsuario
from app.schemas.auth import UsuarioActual
from app.services import adjuntos_service

router = APIRouter(prefix="/adjuntos", tags=["Adjuntos"])

MAX_BYTES = 20 * 1024 * 1024  # 20 MB


class AdjuntoResponse(BaseModel):
    id: uuid.UUID
    entidad: str
    entidad_id: uuid.UUID
    nombre_archivo: str
    content_type: Optional[str] = None
    tamano: Optional[int] = None
    descripcion: Optional[str] = None
    subido_por_nombre: Optional[str] = None
    subido_en: datetime
    model_config = {"from_attributes": True}


def _sanitizar(nombre: str) -> str:
    nombre = (nombre or "archivo").strip().replace("\\", "_").replace("/", "_")
    return re.sub(r"[^A-Za-z0-9._\- ]+", "_", nombre)[:180] or "archivo"


def _to_resp(db: Session, a: AdmAdjunto) -> AdjuntoResponse:
    u = db.get(AdmUsuario, a.subido_por) if a.subido_por else None
    return AdjuntoResponse(
        id=a.id, entidad=a.entidad, entidad_id=a.entidad_id,
        nombre_archivo=a.nombre_archivo, content_type=a.content_type,
        tamano=a.tamano, descripcion=a.descripcion,
        subido_por_nombre=(f"{u.nombre} {u.apellido}" if u else None),
        subido_en=a.subido_en,
    )


@router.get("/{entidad}/{entidad_id}", response_model=list[AdjuntoResponse])
def listar(entidad: str, entidad_id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    rows = db.query(AdmAdjunto).filter(
        AdmAdjunto.entidad == entidad, AdmAdjunto.entidad_id == entidad_id, AdmAdjunto.activo == True
    ).order_by(AdmAdjunto.subido_en.desc()).all()
    return [_to_resp(db, a) for a in rows]


@router.post("/{entidad}/{entidad_id}", response_model=AdjuntoResponse, status_code=201)
async def subir(
    entidad: str, entidad_id: uuid.UUID,
    archivo: UploadFile = File(...),
    descripcion: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    data = await archivo.read()
    if not data:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail=f"El archivo supera el máximo de {MAX_BYTES // (1024*1024)} MB")
    a = adjuntos_service.crear(
        db, entidad, entidad_id, archivo.filename or "archivo", data,
        archivo.content_type, uuid.UUID(actor.id), descripcion=(descripcion or None),
    )
    db.commit()
    db.refresh(a)
    return _to_resp(db, a)


@router.get("/{id}/url")
def url_descarga(id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    a = db.query(AdmAdjunto).filter(AdmAdjunto.id == id, AdmAdjunto.activo == True).first()
    if not a:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    url = almacenamiento.url_descarga(a.storage_key, nombre=a.nombre_archivo)
    return {"url": url, "directo": url is not None}


@router.get("/{id}/raw")
def descargar_raw(id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    a = db.query(AdmAdjunto).filter(AdmAdjunto.id == id, AdmAdjunto.activo == True).first()
    if not a:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    data = almacenamiento.leer(a.storage_key)
    return StreamingResponse(
        iter([data]),
        media_type=a.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{a.nombre_archivo}"'},
    )


@router.delete("/{id}", status_code=204)
def eliminar(id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    a = db.query(AdmAdjunto).filter(AdmAdjunto.id == id, AdmAdjunto.activo == True).first()
    if not a:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    a.activo = False
    db.commit()
    almacenamiento.eliminar(a.storage_key)
    return None
