"""Backfill: lleva los archivos existentes de ope_documento y req_requerimiento
a la tabla unificada adm_adjunto, y repunta el campo al id del adjunto.

Idempotente: si el campo ya es un id de adm_adjunto existente, lo salta.
Uso:  venv/Scripts/python.exe -m scripts.backfill_adjuntos
"""
import uuid
from pathlib import Path

from app.core.database import SessionLocal
from app.models.adjuntos import AdmAdjunto
from app.models.ope import OpeDocumento
from app.models.req import ReqRequerimiento


def _es_adjunto_id(db, valor: str) -> bool:
    try:
        return db.get(AdmAdjunto, uuid.UUID(str(valor))) is not None
    except (ValueError, AttributeError):
        return False


def _crear(db, entidad, entidad_id, key, nombre, subido_por):
    a = AdmAdjunto(
        id=uuid.uuid4(), entidad=entidad, entidad_id=entidad_id,
        nombre_archivo=nombre, storage_key=key, content_type=None,
        tamano=None, subido_por=subido_por,
    )
    db.add(a)
    db.flush()
    return a


def run():
    db = SessionLocal()
    creados = 0
    try:
        # Operaciones
        for d in db.query(OpeDocumento).filter(OpeDocumento.archivo.isnot(None)).all():
            if _es_adjunto_id(db, d.archivo):
                continue
            key = str(d.archivo)
            nombre = Path(key.replace("\\", "/")).name
            a = _crear(db, "ope_documento", d.id, key, nombre, d.creado_por)
            d.archivo = str(a.id)
            creados += 1
            print(f"ope_documento {d.id} -> adjunto {a.id} ({nombre})")

        # Requerimientos
        for r in db.query(ReqRequerimiento).filter(ReqRequerimiento.archivo_ruta.isnot(None)).all():
            if _es_adjunto_id(db, r.archivo_ruta):
                continue
            key = str(r.archivo_ruta)
            nombre = r.archivo_nombre or Path(key.replace("\\", "/")).name
            a = _crear(db, "req_requerimiento", r.id, key, nombre, r.creado_por)
            r.archivo_ruta = str(a.id)
            creados += 1
            print(f"req_requerimiento {r.id} -> adjunto {a.id} ({nombre})")

        db.commit()
        print(f"OK. Adjuntos creados: {creados}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
