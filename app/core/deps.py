from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.admin import AdmModulo, AdmOpcion, AdmPermisoOpcion, AdmUsuario
from app.schemas.auth import UsuarioActual

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UsuarioActual:
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin usuario")

    usuario = db.query(AdmUsuario).filter(
        AdmUsuario.id == user_id,
        AdmUsuario.activo == True,
    ).first()

    if usuario is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    rutas = (
        db.query(AdmOpcion.ruta)
        .join(AdmPermisoOpcion, AdmPermisoOpcion.opcion_id == AdmOpcion.id)
        .filter(
            AdmPermisoOpcion.rol_id == usuario.rol_id,
            AdmPermisoOpcion.puede_ver == True,
            AdmOpcion.activo == True,
        )
        .all()
    )

    # Acciones de módulo: "{modulo}:{accion}" cuando el rol tiene ese permiso en alguna opción
    ACCIONES = ["autorizar", "crear", "editar", "eliminar", "imprimir"]
    modulos_acciones: list[str] = []
    for accion in ACCIONES:
        col = getattr(AdmPermisoOpcion, f"puede_{accion}", None)
        if col is None:
            continue
        modulos_con_accion = (
            db.query(AdmModulo.codigo)
            .join(AdmOpcion, AdmOpcion.modulo_id == AdmModulo.id)
            .join(AdmPermisoOpcion, AdmPermisoOpcion.opcion_id == AdmOpcion.id)
            .filter(
                AdmPermisoOpcion.rol_id == usuario.rol_id,
                col == True,
                AdmOpcion.activo == True,
                AdmModulo.activo == True,
            )
            .distinct()
            .all()
        )
        for (codigo,) in modulos_con_accion:
            modulos_acciones.append(f"{codigo}:{accion}")

    return UsuarioActual(
        id=str(usuario.id),
        email=usuario.email,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        rol_id=str(usuario.rol_id),
        ver_solo_propios=usuario.ver_solo_propios,
        es_asesor=usuario.es_asesor,
        permisos=[r.ruta for r in rutas] + modulos_acciones,
    )
