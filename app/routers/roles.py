from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.core.permisos import require_permission
from app.models.admin import AdmModulo, AdmOpcion, AdmPermisoOpcion, AdmRol, AdmUsuario
from app.schemas.auth import UsuarioActual

SUPERADMIN = "superadmin"


class RolResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    descripcion: str | None = None
    es_superadmin: bool = False
    es_cliente: bool = False
    model_config = {"from_attributes": True}


class RolCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    es_cliente: bool = False


class RolUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    es_cliente: bool | None = None


class OpcionPermiso(BaseModel):
    opcion_id: uuid.UUID
    opcion_nombre: str
    implementada: bool
    puede_ver: bool = False
    puede_crear: bool = False
    puede_editar: bool = False
    puede_eliminar: bool = False
    puede_imprimir: bool = False
    puede_autorizar: bool = False


class GrupoPermiso(BaseModel):
    modulo_codigo: str
    modulo_nombre: str
    opciones: list[OpcionPermiso]


class PermisosUpdate(BaseModel):
    grupos: list[GrupoPermiso]


router = APIRouter(prefix="/roles", tags=["Roles"])


def _get_rol(db: Session, rol_id: uuid.UUID) -> AdmRol:
    rol = db.query(AdmRol).filter(AdmRol.id == rol_id, AdmRol.activo == True).first()
    if not rol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    return rol


def _to_response(rol: AdmRol) -> RolResponse:
    return RolResponse(
        id=rol.id,
        nombre=rol.nombre,
        descripcion=rol.descripcion,
        es_superadmin=rol.nombre.lower() == SUPERADMIN,
        es_cliente=rol.es_cliente,
    )


@router.get("", response_model=list[RolResponse])
def listar(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "ver")),
):
    roles = db.query(AdmRol).filter(AdmRol.activo == True).order_by(AdmRol.nombre).all()
    return [_to_response(r) for r in roles]


@router.post("", response_model=RolResponse, status_code=201)
def crear(
    body: RolCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "crear")),
):
    if body.nombre.lower() == SUPERADMIN:
        raise HTTPException(status_code=400, detail="El nombre 'superadmin' está reservado")
    if db.query(AdmRol).filter(AdmRol.nombre == body.nombre).first():
        raise HTTPException(status_code=409, detail="Ya existe un rol con ese nombre")
    rol = AdmRol(nombre=body.nombre, descripcion=body.descripcion, es_cliente=body.es_cliente, creado_por=uuid.UUID(actor.id))
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return _to_response(rol)


@router.put("/{rol_id}", response_model=RolResponse)
def actualizar(
    rol_id: uuid.UUID,
    body: RolUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "editar")),
):
    rol = _get_rol(db, rol_id)
    if rol.nombre.lower() == SUPERADMIN:
        raise HTTPException(status_code=403, detail="El rol superadmin no puede modificarse")
    if body.nombre:
        rol.nombre = body.nombre
    if body.descripcion is not None:
        rol.descripcion = body.descripcion
    if body.es_cliente is not None:
        rol.es_cliente = body.es_cliente
    db.commit()
    db.refresh(rol)
    return _to_response(rol)


@router.delete("/{rol_id}", status_code=204)
def desactivar(
    rol_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "eliminar")),
):
    rol = _get_rol(db, rol_id)
    if rol.nombre.lower() == SUPERADMIN:
        raise HTTPException(status_code=403, detail="El rol superadmin no puede inactivarse")
    usuarios_activos = db.query(AdmUsuario).filter(
        AdmUsuario.rol_id == rol_id,
        AdmUsuario.activo == True,
    ).count()
    if usuarios_activos > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Este rol tiene {usuarios_activos} usuario{'s' if usuarios_activos > 1 else ''} activo{'s' if usuarios_activos > 1 else ''}. Reasígnalos o inactívalos antes de inactivar el rol.",
        )
    rol.activo = False
    db.commit()


@router.get("/{rol_id}/permisos", response_model=list[GrupoPermiso])
def obtener_permisos(
    rol_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "ver")),
):
    _get_rol(db, rol_id)
    modulos = db.query(AdmModulo).filter(AdmModulo.activo == True).order_by(AdmModulo.orden).all()
    permisos_map = {
        p.opcion_id: p
        for p in db.query(AdmPermisoOpcion).filter(AdmPermisoOpcion.rol_id == rol_id).all()
    }
    grupos = []
    for m in modulos:
        opciones = db.query(AdmOpcion).filter(
            AdmOpcion.modulo_id == m.id, AdmOpcion.activo == True
        ).order_by(AdmOpcion.orden).all()
        if not opciones:
            continue
        grupos.append(GrupoPermiso(
            modulo_codigo=m.codigo,
            modulo_nombre=m.nombre,
            opciones=[
                OpcionPermiso(
                    opcion_id=op.id,
                    opcion_nombre=op.nombre,
                    implementada=op.implementada,
                    puede_ver=permisos_map[op.id].puede_ver if op.id in permisos_map else False,
                    puede_crear=permisos_map[op.id].puede_crear if op.id in permisos_map else False,
                    puede_editar=permisos_map[op.id].puede_editar if op.id in permisos_map else False,
                    puede_eliminar=permisos_map[op.id].puede_eliminar if op.id in permisos_map else False,
                    puede_imprimir=permisos_map[op.id].puede_imprimir if op.id in permisos_map else False,
                    puede_autorizar=permisos_map[op.id].puede_autorizar if op.id in permisos_map else False,
                )
                for op in opciones
            ],
        ))
    return grupos


@router.put("/{rol_id}/permisos", status_code=204)
def guardar_permisos(
    rol_id: uuid.UUID,
    body: PermisosUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "editar")),
):
    rol = _get_rol(db, rol_id)
    if rol.nombre.lower() == SUPERADMIN:
        raise HTTPException(status_code=403, detail="Los permisos del superadmin no pueden modificarse")

    existentes = {
        p.opcion_id: p
        for p in db.query(AdmPermisoOpcion).filter(AdmPermisoOpcion.rol_id == rol_id).all()
    }
    for grupo in body.grupos:
        for item in grupo.opciones:
            p = existentes.get(item.opcion_id)
            if p:
                p.puede_ver      = item.puede_ver
                p.puede_crear    = item.puede_crear
                p.puede_editar   = item.puede_editar
                p.puede_eliminar = item.puede_eliminar
                p.puede_imprimir = item.puede_imprimir
                p.puede_autorizar= item.puede_autorizar
            else:
                db.add(AdmPermisoOpcion(
                    rol_id=rol_id,
                    opcion_id=item.opcion_id,
                    puede_ver=item.puede_ver,
                    puede_crear=item.puede_crear,
                    puede_editar=item.puede_editar,
                    puede_eliminar=item.puede_eliminar,
                    puede_imprimir=item.puede_imprimir,
                    puede_autorizar=item.puede_autorizar,
                ))
    db.commit()
