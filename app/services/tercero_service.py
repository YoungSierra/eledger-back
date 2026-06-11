import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.adm import AdmTercero
from app.models.admin import AdmUsuario
from app.schemas.auth import UsuarioActual
from app.schemas.terceros import TerceroCreate, TerceroResponse, TerceroUpdate


def listar_terceros(
    db: Session,
    tipo_tercero: str | None = None,
    busqueda: str | None = None,
    solo_activos: bool = True,
) -> list[AdmTercero]:
    q = db.query(AdmTercero)
    if solo_activos:
        q = q.filter(AdmTercero.activo == True)
    if tipo_tercero:
        q = q.filter(AdmTercero.tipo_tercero == tipo_tercero)
    if busqueda:
        term = f"%{busqueda}%"
        q = q.filter(
            AdmTercero.nit.ilike(term) |
            AdmTercero.razon_social.ilike(term) |
            AdmTercero.nombre1.ilike(term) |
            AdmTercero.apellido1.ilike(term)
        )
    return q.order_by(AdmTercero.razon_social).limit(200).all()


def _to_response(t: AdmTercero, db: Session) -> TerceroResponse:
    asesor = db.get(AdmUsuario, t.asesor_id) if t.asesor_id else None
    data = TerceroResponse.model_validate(t)
    data.asesor_id = t.asesor_id
    data.asesor_nombre = f"{asesor.nombre} {asesor.apellido}" if asesor else None
    return data


def obtener_tercero(db: Session, tercero_id: uuid.UUID) -> AdmTercero:
    t = db.query(AdmTercero).filter(AdmTercero.id == tercero_id).first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tercero no encontrado")
    return t


def crear_tercero(db: Session, data: TerceroCreate, actor: UsuarioActual) -> AdmTercero:
    t = AdmTercero(**data.model_dump(), creado_por=uuid.UUID(actor.id))
    db.add(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un tercero con NIT {data.nit}",
        )
    db.refresh(t)
    return t


def actualizar_tercero(
    db: Session, tercero_id: uuid.UUID, data: TerceroUpdate, actor: UsuarioActual
) -> AdmTercero:
    t = obtener_tercero(db, tercero_id)
    if data.nit and data.nit != t.nit:
        duplicado = db.query(AdmTercero).filter(
            AdmTercero.nit == data.nit,
            AdmTercero.id != tercero_id,
        ).first()
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un tercero con NIT {data.nit}",
            )
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(t, campo, valor)
    t.modificado_por = uuid.UUID(actor.id)
    t.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(t)
    return t
