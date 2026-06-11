from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.admin import AdmModulo, AdmOpcion, AdmPermisoOpcion
from app.schemas.auth import UsuarioActual

router = APIRouter(prefix="/menu", tags=["Menú"])


class OpcionMenu(BaseModel):
    nombre: str
    ruta: str
    implementada: bool


class GrupoMenu(BaseModel):
    modulo_codigo: str
    modulo_nombre: str
    opciones: list[OpcionMenu]


@router.get("", response_model=list[GrupoMenu])
def obtener_menu(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(get_current_user),
):
    modulos = (
        db.query(AdmModulo)
        .filter(AdmModulo.activo == True)
        .order_by(AdmModulo.orden)
        .all()
    )

    opciones_con_acceso = {
        p.opcion_id
        for p in db.query(AdmPermisoOpcion).filter(
            AdmPermisoOpcion.rol_id == usuario.rol_id,
            AdmPermisoOpcion.puede_ver == True,
        ).all()
    }

    grupos = []
    for m in modulos:
        opciones = (
            db.query(AdmOpcion)
            .filter(
                AdmOpcion.modulo_id == m.id,
                AdmOpcion.activo == True,
                AdmOpcion.id.in_(opciones_con_acceso),
            )
            .order_by(AdmOpcion.orden)
            .all()
        )
        if opciones:
            grupos.append(GrupoMenu(
                modulo_codigo=m.codigo,
                modulo_nombre=m.nombre,
                opciones=[
                    OpcionMenu(nombre=op.nombre, ruta=op.ruta, implementada=op.implementada)
                    for op in opciones
                ],
            ))

    return grupos
