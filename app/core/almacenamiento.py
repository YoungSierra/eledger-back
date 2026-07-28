"""Almacenamiento de archivos: Cloudflare R2 (S3) con fallback local.

Si `settings.r2_enabled` es True usa R2; de lo contrario guarda en UPLOAD_DIR
(solo para desarrollo). El acceso a R2 es privado: la descarga se hace con URL
prefirmada temporal.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import settings

_client = None


def _s3():
    global _client
    if _client is None:
        import boto3
        from botocore.config import Config
        _client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
    return _client


def subir(key: str, body: bytes, content_type: Optional[str] = None) -> None:
    if settings.r2_enabled:
        _s3().put_object(
            Bucket=settings.R2_BUCKET, Key=key, Body=body,
            ContentType=content_type or "application/octet-stream",
        )
    else:
        p = settings.upload_path / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)


def eliminar(key: str) -> None:
    try:
        if settings.r2_enabled:
            _s3().delete_object(Bucket=settings.R2_BUCKET, Key=key)
        else:
            p = settings.upload_path / key
            if p.exists():
                p.unlink()
    except Exception:
        pass  # el borrado del binario no debe bloquear el soft-delete del registro


def url_descarga(key: str, nombre: Optional[str] = None, expires: int = 300) -> Optional[str]:
    """URL prefirmada de descarga (R2). None si es almacenamiento local (usar /raw)."""
    if not settings.r2_enabled:
        return None
    params = {"Bucket": settings.R2_BUCKET, "Key": key}
    if nombre:
        params["ResponseContentDisposition"] = f'attachment; filename="{nombre}"'
    return _s3().generate_presigned_url("get_object", Params=params, ExpiresIn=expires)


def leer(key: str) -> bytes:
    if settings.r2_enabled:
        try:
            obj = _s3().get_object(Bucket=settings.R2_BUCKET, Key=key)
            return obj["Body"].read()
        except Exception:
            # Compatibilidad: archivos antiguos guardados localmente (clave con separador local)
            local = settings.upload_path / key.replace("\\", "/")
            if local.exists():
                return local.read_bytes()
            raise
    return (settings.upload_path / key.replace("\\", "/")).read_bytes()
