"""Servicio de adjuntos: única puerta para registrar archivos en adm_adjunto.

Todo archivo del sistema se guarda como fila en adm_adjunto (referenciada por
entidad + entidad_id) y su binario en R2 vía almacenamiento.
"""
import re
import uuid

from sqlalchemy.orm import Session

from app.core import almacenamiento
from app.models.adjuntos import AdmAdjunto

CARPETAS = {
    "ope_documento": "operaciones/documentos",
    "req_requerimiento": "requerimientos",
}


def sanitizar(nombre: str) -> str:
    nombre = (nombre or "archivo").strip().replace("\\", "_").replace("/", "_")
    return re.sub(r"[^A-Za-z0-9._\- ]+", "_", nombre)[:180] or "archivo"


def crear(db: Session, entidad: str, entidad_id: uuid.UUID, nombre: str, data: bytes,
          content_type: str | None, subido_por: uuid.UUID,
          descripcion: str | None = None, reemplazar_unico: bool = False) -> AdmAdjunto:
    """Sube el binario y crea el registro. Si reemplazar_unico, desactiva los previos
    de esa (entidad, entidad_id) — útil cuando el módulo admite un solo archivo."""
    if reemplazar_unico:
        previos = db.query(AdmAdjunto).filter(
            AdmAdjunto.entidad == entidad, AdmAdjunto.entidad_id == entidad_id, AdmAdjunto.activo == True
        ).all()
        for p in previos:
            p.activo = False
            almacenamiento.eliminar(p.storage_key)

    nombre = sanitizar(nombre)
    carpeta = CARPETAS.get(entidad, entidad)
    key = f"{carpeta}/{entidad_id}/{uuid.uuid4().hex}_{nombre}"
    almacenamiento.subir(key, data, content_type)
    a = AdmAdjunto(
        id=uuid.uuid4(), entidad=entidad, entidad_id=entidad_id,
        nombre_archivo=nombre, storage_key=key, content_type=content_type,
        tamano=len(data), descripcion=descripcion, subido_por=subido_por,
    )
    db.add(a)
    db.flush()
    return a


def listar(db: Session, entidad: str, entidad_id: uuid.UUID) -> list[AdmAdjunto]:
    return db.query(AdmAdjunto).filter(
        AdmAdjunto.entidad == entidad, AdmAdjunto.entidad_id == entidad_id, AdmAdjunto.activo == True
    ).order_by(AdmAdjunto.subido_en.desc()).all()


def primero(db: Session, entidad: str, entidad_id: uuid.UUID) -> AdmAdjunto | None:
    return db.query(AdmAdjunto).filter(
        AdmAdjunto.entidad == entidad, AdmAdjunto.entidad_id == entidad_id, AdmAdjunto.activo == True
    ).order_by(AdmAdjunto.subido_en.desc()).first()
