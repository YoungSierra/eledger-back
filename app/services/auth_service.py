import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.admin import AdmSesion, AdmUsuario
from app.schemas.auth import TokenResponse


def _crear_tokens(db: Session, usuario: AdmUsuario, ip: str | None = None) -> TokenResponse:
    access_token = create_access_token({
        "sub": str(usuario.id),
        "email": usuario.email,
        "rol_id": str(usuario.rol_id),
    })

    refresh_token = secrets.token_urlsafe(48)
    expira = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    sesion = AdmSesion(
        usuario_id=usuario.id,
        refresh_token=refresh_token,
        expira_en=expira,
        ip=ip,
    )
    db.add(sesion)

    usuario.ultimo_acceso = datetime.now(timezone.utc)

    from app.models.admin import AdmRol
    rol = db.query(AdmRol).filter(AdmRol.id == usuario.rol_id).first()
    es_cliente = rol.es_cliente if rol else False

    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, es_cliente=es_cliente)


def login(db: Session, email: str, password: str, ip: str | None = None) -> TokenResponse:
    usuario = db.query(AdmUsuario).filter(AdmUsuario.email == email).first()

    if not usuario or not verify_password(password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo — contacta al administrador",
        )

    return _crear_tokens(db, usuario, ip)


def refresh(db: Session, refresh_token: str) -> TokenResponse:
    ahora = datetime.now(timezone.utc)

    sesion = db.query(AdmSesion).filter(
        AdmSesion.refresh_token == refresh_token,
        AdmSesion.expira_en > ahora,
    ).first()

    if not sesion:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada",
        )

    usuario = db.query(AdmUsuario).filter(
        AdmUsuario.id == sesion.usuario_id,
        AdmUsuario.activo == True,
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    # Rotar refresh token: elimina el anterior y crea uno nuevo
    db.delete(sesion)
    db.flush()

    return _crear_tokens(db, usuario, sesion.ip)


def logout(db: Session, refresh_token: str) -> None:
    sesion = db.query(AdmSesion).filter(
        AdmSesion.refresh_token == refresh_token
    ).first()

    if sesion:
        db.delete(sesion)
        db.commit()
