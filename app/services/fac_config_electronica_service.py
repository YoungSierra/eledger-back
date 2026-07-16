"""
Configuración del proveedor de facturación electrónica.

Fila única por empresa (una empresa = una BD). El token del PTH se guarda
cifrado y nunca sale por la API en claro: solo enmascarado.
"""
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.auditoria import registrar as audit
from app.core.cifrado import cifrar, descifrar, enmascarar
from app.models.facturacion import FacConfigElectronica
from app.schemas.auth import UsuarioActual
from app.schemas.fac_config_electronica import ConfigElectronicaUpdate

# Única base verificada de Dataico (probada: responde). La de habilitación /
# pruebas NO está publicada — la entrega Dataico al onboarding, por eso `base_url`
# es un campo editable en vez de una constante adivinada aquí.
DATAICO_BASE_PRODUCCION = "https://api.dataico.com/direct/dataico_api/v2"


def _base_url(cfg: FacConfigElectronica) -> str:
    return ((cfg.credenciales or {}).get("base_url") or "").rstrip("/") or DATAICO_BASE_PRODUCCION


def obtener(db: Session) -> FacConfigElectronica | None:
    return db.query(FacConfigElectronica).first()


def _a_respuesta(cfg: FacConfigElectronica | None) -> dict | None:
    if not cfg:
        return None
    cred = cfg.credenciales or {}
    token = descifrar(cred.get("auth_token", ""))
    return {
        "id": cfg.id,
        "proveedor": cfg.proveedor,
        "nombre_pth": cfg.nombre_pth,
        "ambiente": cfg.ambiente,
        "activo": cfg.activo,
        "account_id": cred.get("account_id"),
        "base_url": cred.get("base_url") or "",
        "auth_token_mascara": enmascarar(token) or None,
        "tiene_token": bool(token),
        "modificado_en": cfg.modificado_en,
    }


def obtener_para_api(db: Session) -> dict | None:
    return _a_respuesta(obtener(db))


def guardar(db: Session, data: ConfigElectronicaUpdate, actor: UsuarioActual) -> dict:
    actor_id = uuid.UUID(actor.id)
    cfg = obtener(db)
    nuevo = cfg is None

    cred_previas = (cfg.credenciales if cfg else None) or {}
    # auth_token None => el usuario no lo tocó: se conserva el cifrado anterior.
    if data.auth_token is None:
        token_cifrado = cred_previas.get("auth_token", "")
    elif data.auth_token == "":
        token_cifrado = ""
    else:
        token_cifrado = cifrar(data.auth_token)

    if data.activo and data.proveedor == "DATAICO" and not token_cifrado:
        raise HTTPException(status_code=400, detail="Dataico requiere el Auth-Token para activar la integración")

    credenciales = {
        "account_id": data.account_id or "",
        "auth_token": token_cifrado,
        "base_url": (data.base_url or "").strip(),
    }

    if nuevo:
        cfg = FacConfigElectronica(
            proveedor=data.proveedor,
            nombre_pth=data.nombre_pth,
            credenciales=credenciales,
            ambiente=data.ambiente,
            activo=data.activo,
            creado_por=actor_id,
        )
        db.add(cfg)
    else:
        cfg.proveedor = data.proveedor
        cfg.nombre_pth = data.nombre_pth
        cfg.credenciales = credenciales
        cfg.ambiente = data.ambiente
        cfg.activo = data.activo
        cfg.modificado_por = actor_id
        cfg.modificado_en = datetime.now(timezone.utc)

    db.flush()
    # El token jamás entra en el contexto de auditoría.
    audit(db, "fac_config_electronica", cfg.id, "INSERT" if nuevo else "UPDATE", actor_id,
          contexto={"proveedor": cfg.proveedor, "ambiente": cfg.ambiente, "activo": cfg.activo})
    db.commit()
    db.refresh(cfg)
    return _a_respuesta(cfg)


def probar_conexion(db: Session) -> tuple[bool, str]:
    cfg = obtener(db)
    if not cfg:
        return False, "No hay configuración guardada."
    if cfg.proveedor != "DATAICO":
        return False, f"La prueba de conexión aún no está implementada para {cfg.proveedor}."

    cred = cfg.credenciales or {}
    account_id = cred.get("account_id") or ""
    token = descifrar(cred.get("auth_token", ""))
    if not account_id or not token:
        return False, "Faltan Account ID o Auth-Token."

    url = f"{_base_url(cfg)}/invoices"
    try:
        r = httpx.get(
            url,
            headers={"Dataico_account_id": account_id, "Auth-Token": token},
            params={"number": "__ping__"},
            timeout=10.0,
        )
    except httpx.RequestError as e:
        return False, f"No se pudo contactar a Dataico: {e.__class__.__name__}"

    if r.status_code in (401, 403):
        return False, "Credenciales rechazadas por Dataico (401/403). Revisa Account ID y Auth-Token."
    if r.status_code >= 500:
        return False, f"Dataico respondió {r.status_code}. Reintenta más tarde."
    # 200 o 404 significan que autenticó: 404 es "esa factura no existe",
    # que es justo lo esperado para un número inventado.
    return True, f"Conexión correcta con Dataico ({cfg.ambiente})."
