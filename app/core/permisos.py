from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.admin import AdmModulo, AdmOpcion, AdmPermisoOpcion
from app.schemas.auth import UsuarioActual


def require_permission(modulo: str, accion: str):
    """
    Verifica que el usuario tenga la acción requerida en al menos una opción del módulo.
    Uso: Depends(require_permission("administracion", "crear"))
    """
    def checker(
        current_user: UsuarioActual = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> UsuarioActual:
        columna = f"puede_{accion}"
        tiene = (
            db.query(AdmPermisoOpcion)
            .join(AdmOpcion, AdmPermisoOpcion.opcion_id == AdmOpcion.id)
            .join(AdmModulo, AdmOpcion.modulo_id == AdmModulo.id)
            .filter(
                AdmPermisoOpcion.rol_id == current_user.rol_id,
                AdmModulo.codigo == modulo,
                AdmModulo.activo == True,
                AdmOpcion.activo == True,
                getattr(AdmPermisoOpcion, columna) == True,
            )
            .first()
        )

        if not tiene:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso para '{accion}' en módulo '{modulo}'",
            )

        return current_user

    return checker
