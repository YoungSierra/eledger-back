import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.admin import AdmRol, AdmUsuario
from app.schemas.auth import UsuarioActual
from app.schemas.usuarios import UsuarioCreate, UsuarioUpdate


def listar_usuarios(db: Session, solo_activos: bool = True) -> list[AdmUsuario]:
    q = db.query(AdmUsuario)
    if solo_activos:
        q = q.filter(AdmUsuario.activo == True)
    return q.order_by(AdmUsuario.nombre, AdmUsuario.apellido).all()


def obtener_usuario(db: Session, usuario_id: uuid.UUID) -> AdmUsuario:
    u = db.query(AdmUsuario).filter(AdmUsuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return u


def crear_usuario(db: Session, data: UsuarioCreate, actor: UsuarioActual) -> AdmUsuario:
    existente = db.query(AdmUsuario).filter(AdmUsuario.email == data.email).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo ya está en uso")

    rol = db.query(AdmRol).filter(AdmRol.id == data.rol_id, AdmRol.activo == True).first()
    if not rol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    usuario = AdmUsuario(
        email=data.email,
        nombre=data.nombre,
        apellido=data.apellido,
        password_hash=hash_password(data.password),
        rol_id=data.rol_id,
        tercero_id=data.tercero_id,
        es_asesor=data.es_asesor,
        ver_solo_propios=data.ver_solo_propios,
        creado_por=actor.id,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_usuario(
    db: Session, usuario_id: uuid.UUID, data: UsuarioUpdate, actor: UsuarioActual
) -> AdmUsuario:
    from datetime import datetime, timezone

    u = obtener_usuario(db, usuario_id)

    if data.nombre is not None:
        u.nombre = data.nombre
    if data.apellido is not None:
        u.apellido = data.apellido
    if data.rol_id is not None:
        rol = db.query(AdmRol).filter(AdmRol.id == data.rol_id, AdmRol.activo == True).first()
        if not rol:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
        u.rol_id = data.rol_id
    if data.tercero_id is not None:
        u.tercero_id = data.tercero_id
    if data.password is not None:
        u.password_hash = hash_password(data.password)
    if data.es_asesor is not None:
        u.es_asesor = data.es_asesor
    if data.ver_solo_propios is not None:
        u.ver_solo_propios = data.ver_solo_propios
    if data.activo is not None:
        u.activo = data.activo

    u.modificado_por = actor.id
    u.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(u)
    return u


def desactivar_usuario(db: Session, usuario_id: uuid.UUID, actor: UsuarioActual) -> None:
    from datetime import datetime, timezone

    u = obtener_usuario(db, usuario_id)
    if u.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propio usuario",
        )
    u.activo = False
    u.modificado_por = actor.id
    u.modificado_en = datetime.now(timezone.utc)
    db.commit()
