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
from app.services.emisores import factus

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
    secret = descifrar(cred.get("client_secret", ""))
    password = descifrar(cred.get("password", ""))
    return {
        "id": cfg.id,
        "proveedor": cfg.proveedor,
        "nombre_pth": cfg.nombre_pth,
        "ambiente": cfg.ambiente,
        "activo": cfg.activo,
        "account_id": cred.get("account_id"),
        "base_url": cred.get("base_url") or "",
        "test_prefix": cred.get("test_prefix") or "",
        "test_resolution_number": cred.get("test_resolution_number") or "",
        "auth_token_mascara": enmascarar(token) or None,
        "tiene_token": bool(token),
        # Factus — los secretos solo salen enmascarados, igual que el token de Dataico.
        "client_id": cred.get("client_id") or "",
        "username": cred.get("username") or "",
        "numbering_range_id": cred.get("numbering_range_id") or "",
        "client_secret_mascara": enmascarar(secret) or None,
        "password_mascara": enmascarar(password) or None,
        "tiene_client_secret": bool(secret),
        "tiene_password": bool(password),
        "modificado_en": cfg.modificado_en,
    }


def obtener_para_api(db: Session) -> dict | None:
    return _a_respuesta(obtener(db))


def guardar(db: Session, data: ConfigElectronicaUpdate, actor: UsuarioActual) -> dict:
    actor_id = uuid.UUID(actor.id)
    cfg = obtener(db)
    nuevo = cfg is None

    cred_previas = (cfg.credenciales if cfg else None) or {}

    def _secreto(nuevo: str | None, clave: str) -> str:
        """None => el usuario no lo tocó (conservar) · "" => borrar · valor => cifrar."""
        if nuevo is None:
            return cred_previas.get(clave, "")
        return "" if nuevo == "" else cifrar(nuevo)

    token_cifrado = _secreto(data.auth_token, "auth_token")
    secret_cifrado = _secreto(data.client_secret, "client_secret")
    password_cifrado = _secreto(data.password, "password")

    if data.activo and data.proveedor == "DATAICO" and not token_cifrado:
        raise HTTPException(status_code=400, detail="Dataico requiere el Auth-Token para activar la integración")
    if data.activo and data.proveedor == "PTH_FACTUS" and not (secret_cifrado and password_cifrado):
        raise HTTPException(status_code=400, detail="Factus requiere el Client Secret y la contraseña para activar la integración")

    credenciales = {
        "account_id": data.account_id or "",
        "auth_token": token_cifrado,
        "base_url": (data.base_url or "").strip(),
        "test_prefix": (data.test_prefix or "").strip(),
        "test_resolution_number": (data.test_resolution_number or "").strip(),
        # Factus
        "client_id": (data.client_id or "").strip(),
        "client_secret": secret_cifrado,
        "username": (data.username or "").strip(),
        "password": password_cifrado,
        "numbering_range_id": (data.numbering_range_id or "").strip(),
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

    if cfg.proveedor == "PTH_FACTUS":
        # El adaptador autentica por OAuth2 y lista los rangos de numeración:
        # así el usuario ve qué ID poner en "Rango de numeración".
        cred = cfg.credenciales or {}
        return factus.probar_conexion(
            {
                "client_id": cred.get("client_id"),
                "client_secret": descifrar(cred.get("client_secret", "")),
                "username": cred.get("username"),
                "password": descifrar(cred.get("password", "")),
            },
            (cred.get("base_url") or "").strip(),
            cfg.ambiente,
        )

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
