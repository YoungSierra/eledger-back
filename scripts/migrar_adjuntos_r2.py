"""Migra a R2 los binarios de adm_adjunto que todavía están en almacenamiento local.

Para cada adjunto cuyo storage_key exista como archivo local (UPLOAD_DIR), sube el
contenido a R2 bajo una clave con el esquema nuevo y actualiza storage_key/tamano.
Idempotente: si el archivo ya no está local (ya en R2), lo salta.

Uso:  venv/Scripts/python.exe -m scripts.migrar_adjuntos_r2
"""
import mimetypes
import uuid

from app.core.config import settings
from app.core.database import SessionLocal
from app.core import almacenamiento
from app.models.adjuntos import AdmAdjunto
from app.services.adjuntos_service import CARPETAS, sanitizar


def run():
    if not settings.r2_enabled:
        print("R2 no está habilitado; nada que migrar.")
        return
    db = SessionLocal()
    migrados = 0
    try:
        for a in db.query(AdmAdjunto).filter(AdmAdjunto.activo == True).all():
            local = settings.upload_path / str(a.storage_key).replace("\\", "/")
            if not local.exists():
                continue  # ya está en R2 (o no hay binario local)
            data = local.read_bytes()
            ctype = a.content_type or mimetypes.guess_type(a.nombre_archivo)[0] or "application/octet-stream"
            carpeta = CARPETAS.get(a.entidad, a.entidad)
            new_key = f"{carpeta}/{a.entidad_id}/{uuid.uuid4().hex}_{sanitizar(a.nombre_archivo)}"
            almacenamiento.subir(new_key, data, ctype)
            print(f"  {a.entidad}/{a.entidad_id} : {a.storage_key}  ->  {new_key}")
            a.storage_key = new_key
            a.content_type = ctype
            a.tamano = len(data)
            migrados += 1
        db.commit()
        print(f"OK. Binarios migrados a R2: {migrados}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
