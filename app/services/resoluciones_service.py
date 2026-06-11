import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.facturacion import FacResolucion
from app.schemas.auth import UsuarioActual
from app.schemas.resoluciones import ResolucionCreate, ResolucionUpdate, ResolucionResponse


def _enrich(obj: FacResolucion) -> ResolucionResponse:
    hoy = date.today()
    disponibles = max(0, obj.rango_hasta - (obj.rango_desde + obj.consecutivo_actual - 1))
    return ResolucionResponse(
        id=obj.id, tipo=obj.tipo,
        numero_resolucion=obj.numero_resolucion,
        prefijo=obj.prefijo,
        rango_desde=obj.rango_desde, rango_hasta=obj.rango_hasta,
        consecutivo_actual=obj.consecutivo_actual,
        fecha_desde=obj.fecha_desde, fecha_hasta=obj.fecha_hasta,
        activo=obj.activo,
        disponibles=disponibles,
        vencida=obj.fecha_hasta < hoy,
    )


def obtener_activa(db: Session) -> ResolucionResponse | None:
    hoy = date.today()
    obj = (
        db.query(FacResolucion)
        .filter(
            FacResolucion.tipo == "FACTURA_VENTA",
            FacResolucion.activo == True,
            FacResolucion.fecha_desde <= hoy,
            FacResolucion.fecha_hasta >= hoy,
        )
        .first()
    )
    return _enrich(obj) if obj else None


def listar(db: Session, solo_activas: bool = False) -> list[ResolucionResponse]:
    q = db.query(FacResolucion)
    if solo_activas:
        q = q.filter(FacResolucion.activo == True)
    return [_enrich(o) for o in q.order_by(FacResolucion.tipo, FacResolucion.fecha_hasta.desc()).all()]


def crear(db: Session, data: ResolucionCreate, actor: UsuarioActual) -> ResolucionResponse:
    obj = FacResolucion(
        **data.model_dump(),
        consecutivo_actual=0,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return _enrich(obj)


def actualizar(db: Session, id: uuid.UUID, data: ResolucionUpdate, actor: UsuarioActual) -> ResolucionResponse:
    obj = db.query(FacResolucion).filter(FacResolucion.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resolución no encontrada")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return _enrich(obj)
