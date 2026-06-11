from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.models.admin import AdmUsuario
from app.schemas.auth import (
    LoginRequest, LogoutRequest, RefreshRequest,
    TokenResponse, UsuarioActual,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class ActualizarPerfilRequest(BaseModel):
    nombre: str
    apellido: str


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nuevo: str


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    return auth_service.login(db, body.email, body.password, ip)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh(db, body.refresh_token)


@router.post("/logout", status_code=204)
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    auth_service.logout(db, body.refresh_token)


@router.get("/me", response_model=UsuarioActual)
def me(current_user: UsuarioActual = Depends(get_current_user)):
    return current_user


@router.put("/me/perfil", response_model=UsuarioActual)
def actualizar_perfil(
    body: ActualizarPerfilRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    import uuid
    u = db.query(AdmUsuario).filter(AdmUsuario.id == uuid.UUID(actor.id)).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u.nombre = body.nombre.strip()
    u.apellido = body.apellido.strip()
    db.commit()
    db.refresh(u)
    return actor.__class__(
        id=actor.id, email=actor.email,
        nombre=u.nombre, apellido=u.apellido,
        rol_id=actor.rol_id, permisos=actor.permisos,
    )


@router.post("/me/cambiar-password", status_code=204)
def cambiar_password(
    body: CambiarPasswordRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    import uuid
    u = db.query(AdmUsuario).filter(AdmUsuario.id == uuid.UUID(actor.id)).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not verify_password(body.password_actual, u.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")
    u.password_hash = hash_password(body.password_nuevo)
    db.commit()
