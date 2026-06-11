import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ope import OpeAerolinea, OpeAeropuerto, OpeConcepto
from app.schemas.auth import UsuarioActual
from app.schemas.ope import (
    OpeAerolineaCreate, OpeAerolineaUpdate,
    OpeAeropuertoCreate, OpeAeropuertoUpdate,
    OpeConceptoCreate, OpeConceptoUpdate,
)


# ---------------------------------------------------------------------------
# Aerolínea
# ---------------------------------------------------------------------------

def listar_aerolineas(db: Session, solo_activas: bool = True) -> list[OpeAerolinea]:
    q = db.query(OpeAerolinea)
    if solo_activas:
        q = q.filter(OpeAerolinea.activo == True)
    return q.order_by(OpeAerolinea.nombre).all()


def obtener_aerolinea(db: Session, aerolinea_id: uuid.UUID) -> OpeAerolinea:
    a = db.query(OpeAerolinea).filter(OpeAerolinea.id == aerolinea_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aerolínea no encontrada")
    return a


def crear_aerolinea(db: Session, data: OpeAerolineaCreate, actor: UsuarioActual) -> OpeAerolinea:
    if db.query(OpeAerolinea).filter(OpeAerolinea.codigo_iata == data.codigo_iata).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Ya existe la aerolínea {data.codigo_iata}")
    a = OpeAerolinea(codigo_iata=data.codigo_iata, nombre=data.nombre, modalidad=data.modalidad)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def actualizar_aerolinea(db: Session, aerolinea_id: uuid.UUID, data: OpeAerolineaUpdate, actor: UsuarioActual) -> OpeAerolinea:
    a = obtener_aerolinea(db, aerolinea_id)
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(a, campo, valor)
    db.commit()
    db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# Aeropuerto
# ---------------------------------------------------------------------------

def listar_aeropuertos(db: Session, solo_activos: bool = True, busqueda: str | None = None) -> list[OpeAeropuerto]:
    q = db.query(OpeAeropuerto)
    if solo_activos:
        q = q.filter(OpeAeropuerto.activo == True)
    if busqueda:
        term = f"%{busqueda}%"
        q = q.filter(
            OpeAeropuerto.codigo_iata.ilike(term) |
            OpeAeropuerto.nombre.ilike(term) |
            OpeAeropuerto.ciudad.ilike(term)
        )
    return q.order_by(OpeAeropuerto.nombre).limit(100).all()


def obtener_aeropuerto(db: Session, aeropuerto_id: uuid.UUID) -> OpeAeropuerto:
    a = db.query(OpeAeropuerto).filter(OpeAeropuerto.id == aeropuerto_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aeropuerto no encontrado")
    return a


def crear_aeropuerto(db: Session, data: OpeAeropuertoCreate, actor: UsuarioActual) -> OpeAeropuerto:
    if db.query(OpeAeropuerto).filter(OpeAeropuerto.codigo_iata == data.codigo_iata).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Ya existe el aeropuerto {data.codigo_iata}")
    a = OpeAeropuerto(**data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def actualizar_aeropuerto(db: Session, aeropuerto_id: uuid.UUID, data: OpeAeropuertoUpdate, actor: UsuarioActual) -> OpeAeropuerto:
    a = obtener_aeropuerto(db, aeropuerto_id)
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(a, campo, valor)
    db.commit()
    db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# Concepto tarifario
# ---------------------------------------------------------------------------

def listar_conceptos(db: Session, seccion: str | None = None, solo_activos: bool = True) -> list[OpeConcepto]:
    q = db.query(OpeConcepto)
    if solo_activos:
        q = q.filter(OpeConcepto.activo == True)
    if seccion:
        q = q.filter(OpeConcepto.seccion == seccion)
    return q.order_by(OpeConcepto.seccion, OpeConcepto.nombre).all()


def obtener_concepto(db: Session, concepto_id: uuid.UUID) -> OpeConcepto:
    c = db.query(OpeConcepto).filter(OpeConcepto.id == concepto_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concepto no encontrado")
    return c


def crear_concepto(db: Session, data: OpeConceptoCreate, actor: UsuarioActual) -> OpeConcepto:
    c = OpeConcepto(**data.model_dump(), creado_por=uuid.UUID(actor.id))
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def actualizar_concepto(db: Session, concepto_id: uuid.UUID, data: OpeConceptoUpdate, actor: UsuarioActual) -> OpeConcepto:
    c = obtener_concepto(db, concepto_id)
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(c, campo, valor)
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c
