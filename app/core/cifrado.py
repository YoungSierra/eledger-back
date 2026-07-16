"""
Cifrado simétrico para secretos que se guardan en BD (credenciales del PTH).

Fernet (AES-128-CBC + HMAC). La clave sale de `FE_ENCRYPTION_KEY`; si está
vacía se deriva de `JWT_SECRET` para no exigir configuración extra en dev.

Advertencia: si se deriva de JWT_SECRET y este se rota, lo ya cifrado queda
indescifrable. En producción fijar FE_ENCRYPTION_KEY explícitamente y no
perderla. Generar una con:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_MASCARA = "••••••••"


def _fernet() -> Fernet:
    clave = (settings.FE_ENCRYPTION_KEY or "").strip()
    if clave:
        return Fernet(clave.encode())
    # Derivación determinística desde JWT_SECRET: SHA-256 -> 32 bytes -> base64url,
    # que es exactamente el formato de clave que Fernet espera.
    derivada = base64.urlsafe_b64encode(hashlib.sha256(settings.JWT_SECRET.encode()).digest())
    return Fernet(derivada)


def cifrar(texto: str) -> str:
    if texto is None or texto == "":
        return ""
    return _fernet().encrypt(texto.encode()).decode()


def descifrar(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        # Clave cambiada o dato corrupto: no se puede recuperar. Se devuelve
        # vacío para que el llamador lo trate como "sin credencial" en vez de
        # reventar la pantalla de configuración.
        return ""


def enmascarar(texto: str) -> str:
    """Muestra solo los últimos 4 caracteres. Para devolver por API sin exponer."""
    if not texto:
        return ""
    return _MASCARA + texto[-4:] if len(texto) > 4 else _MASCARA
