import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ope import OpeAerolinea, OpeAeropuerto, OpeConcepto, OpeConceptoRetencion
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

def _attach_concepto(c: OpeConcepto) -> OpeConcepto:
    c.cuenta_ingreso_nombre = f"{c.cuenta_ingreso.codigo} — {c.cuenta_ingreso.nombre}" if c.cuenta_ingreso else None
    c.cuenta_devolucion_venta_nombre = f"{c.cuenta_devolucion_venta.codigo} — {c.cuenta_devolucion_venta.nombre}" if c.cuenta_devolucion_venta else None
    c.tarifa_iva_nombre = c.tarifa_iva.nombre if c.tarifa_iva else None
    c.um_codigo = c.um.codigo if c.um else None
    vinculos = [v for v in c.retenciones if v.activo]
    c.retenciones_ids = [v.retencion_id for v in vinculos]
    c.retenciones_nombres = [f"{v.retencion.nombre} ({v.retencion.porcentaje:g}%)" for v in vinculos if v.retencion]
    return c


def _fijar_retenciones(db: Session, concepto: OpeConcepto, ids) -> None:
    """Reemplaza las retenciones del concepto por la lista recibida."""
    if ids is None:
        return
    actuales = {v.retencion_id: v for v in concepto.retenciones}
    for rid in ids:
        if rid in actuales:
            actuales[rid].activo = True
        else:
            db.add(OpeConceptoRetencion(id=uuid.uuid4(), concepto_id=concepto.id,
                                        retencion_id=rid, activo=True))
    for rid, v in actuales.items():
        if rid not in ids:
            db.delete(v)


def listar_conceptos(db: Session, seccion: str | None = None, solo_activos: bool = True) -> list[OpeConcepto]:
    q = db.query(OpeConcepto)
    if solo_activos:
        q = q.filter(OpeConcepto.activo == True)
    if seccion:
        q = q.filter(OpeConcepto.seccion == seccion)
    return [_attach_concepto(c) for c in q.order_by(OpeConcepto.seccion, OpeConcepto.nombre).all()]


def obtener_concepto(db: Session, concepto_id: uuid.UUID) -> OpeConcepto:
    c = db.query(OpeConcepto).filter(OpeConcepto.id == concepto_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concepto no encontrado")
    return _attach_concepto(c)


def crear_concepto(db: Session, data: OpeConceptoCreate, actor: UsuarioActual) -> OpeConcepto:
    campos = data.model_dump()
    retenciones = campos.pop("retenciones_ids", [])
    c = OpeConcepto(**campos, creado_por=uuid.UUID(actor.id))
    db.add(c)
    db.flush()
    _fijar_retenciones(db, c, retenciones)
    db.commit()
    db.refresh(c)
    return _attach_concepto(c)


def actualizar_concepto(db: Session, concepto_id: uuid.UUID, data: OpeConceptoUpdate, actor: UsuarioActual) -> OpeConcepto:
    c = obtener_concepto(db, concepto_id)
    campos = data.model_dump(exclude_none=True)
    retenciones = campos.pop("retenciones_ids", None)
    for campo, valor in campos.items():
        setattr(c, campo, valor)
    _fijar_retenciones(db, c, retenciones)
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return _attach_concepto(c)
