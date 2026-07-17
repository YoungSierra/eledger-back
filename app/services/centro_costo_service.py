import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contabilidad import CntCentroCosto
from app.schemas.auth import UsuarioActual
from app.schemas.centros_costo import CentroCostoCreate, CentroCostoUpdate


def listar(db: Session, padre_id: uuid.UUID | None = None, solo_activos: bool = True, busqueda: str | None = None, plano: bool = False) -> list[CntCentroCosto]:
    q = db.query(CntCentroCosto)
    if solo_activos:
        q = q.filter(CntCentroCosto.activo == True)
    if busqueda:
        term = f"%{busqueda}%"
        return q.filter(
            (CntCentroCosto.codigo.ilike(term)) | (CntCentroCosto.nombre.ilike(term))
        ).order_by(CntCentroCosto.codigo).limit(100).all()
    if plano:
        # Lista completa (todos los niveles) para selectores de transacciones.
        return q.order_by(CntCentroCosto.codigo).all()
    if padre_id is not None:
        q = q.filter(CntCentroCosto.padre_id == padre_id)
    else:
        q = q.filter(CntCentroCosto.padre_id.is_(None))
    return q.order_by(CntCentroCosto.codigo).all()


def obtener(db: Session, centro_id: uuid.UUID) -> CntCentroCosto:
    c = db.query(CntCentroCosto).filter(CntCentroCosto.id == centro_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centro de costo no encontrado")
    return c


def crear(db: Session, data: CentroCostoCreate, actor: UsuarioActual) -> CntCentroCosto:
    if db.query(CntCentroCosto).filter(CntCentroCosto.codigo == data.codigo).first():
        raise HTTPException(status_code=409, detail=f"Ya existe el centro de costo {data.codigo}")
    c = CntCentroCosto(
        codigo=data.codigo,
        nombre=data.nombre,
        padre_id=data.padre_id,
        descripcion=data.descripcion,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def actualizar(db: Session, centro_id: uuid.UUID, data: CentroCostoUpdate, actor: UsuarioActual) -> CntCentroCosto:
    c = obtener(db, centro_id)
    if data.nombre is not None:
        c.nombre = data.nombre
    if data.descripcion is not None:
        c.descripcion = data.descripcion
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


def desactivar(db: Session, centro_id: uuid.UUID, actor: UsuarioActual) -> None:
    c = obtener(db, centro_id)
    hijos = db.query(CntCentroCosto).filter(CntCentroCosto.padre_id == centro_id, CntCentroCosto.activo == True).count()
    if hijos:
        raise HTTPException(status_code=400, detail="No se puede desactivar un centro con subcentros activos")
    c.activo = False
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()


def reactivar(db: Session, centro_id: uuid.UUID, actor: UsuarioActual) -> CntCentroCosto:
    c = db.query(CntCentroCosto).filter(CntCentroCosto.id == centro_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Centro de costo no encontrado")
    c.activo = True
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c
