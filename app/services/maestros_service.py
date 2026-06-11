import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.admin import AdmCondicionPago, AdmTarifaIva, AdmRetencion, AdmMoneda
from app.models.contabilidad import CntCuenta
from app.schemas.auth import UsuarioActual
from app.schemas.maestros import (
    MonedaCreate, MonedaUpdate, MonedaResponse,
    CondicionPagoCreate, CondicionPagoUpdate,
    TarifaIvaCreate, TarifaIvaUpdate, TarifaIvaResponse,
    RetencionCreate, RetencionUpdate, RetencionResponse,
)


# ---------------------------------------------------------------------------
# Monedas
# ---------------------------------------------------------------------------

def listar_monedas(db: Session, solo_activas: bool = False) -> list[AdmMoneda]:
    q = db.query(AdmMoneda)
    if solo_activas:
        q = q.filter(AdmMoneda.activo == True)
    return q.order_by(AdmMoneda.codigo).all()


def crear_moneda(db: Session, data: MonedaCreate, actor: UsuarioActual) -> AdmMoneda:
    if db.query(AdmMoneda).filter(AdmMoneda.codigo == data.codigo.upper()).first():
        raise HTTPException(status_code=400, detail="Ya existe una moneda con ese código")
    if data.es_funcional:
        db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True).update({"es_funcional": False})
    obj = AdmMoneda(
        codigo=data.codigo.upper(), nombre=data.nombre, simbolo=data.simbolo,
        decimales=data.decimales, es_funcional=data.es_funcional,
        activo=True, creado_por=uuid.UUID(actor.id),
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def actualizar_moneda(db: Session, id: uuid.UUID, data: MonedaUpdate, actor: UsuarioActual) -> AdmMoneda:
    obj = db.query(AdmMoneda).filter(AdmMoneda.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moneda no encontrada")
    if data.es_funcional:
        db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.id != id).update({"es_funcional": False})
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return obj


def _cuenta_info(db: Session, cuenta_id) -> tuple[str | None, str | None]:
    if not cuenta_id:
        return None, None
    c = db.query(CntCuenta).filter(CntCuenta.id == cuenta_id).first()
    return (c.codigo, c.nombre) if c else (None, None)


def _enrich_iva(db: Session, obj: AdmTarifaIva) -> TarifaIvaResponse:
    vc, vn = _cuenta_info(db, obj.cuenta_iva_ventas_id)
    cc, cn = _cuenta_info(db, obj.cuenta_iva_compras_id)
    return TarifaIvaResponse(
        id=obj.id, nombre=obj.nombre, tipo=obj.tipo,
        porcentaje=obj.porcentaje, activo=obj.activo,
        cuenta_iva_ventas_id=obj.cuenta_iva_ventas_id,
        cuenta_iva_ventas_codigo=vc, cuenta_iva_ventas_nombre=vn,
        cuenta_iva_compras_id=obj.cuenta_iva_compras_id,
        cuenta_iva_compras_codigo=cc, cuenta_iva_compras_nombre=cn,
    )


def _enrich_ret(db: Session, obj: AdmRetencion) -> RetencionResponse:
    cc, cn = _cuenta_info(db, obj.cuenta_compras_id)
    vc, vn = _cuenta_info(db, obj.cuenta_ventas_id)
    return RetencionResponse(
        id=obj.id, tipo=obj.tipo, nombre=obj.nombre,
        porcentaje=obj.porcentaje, base_minima=obj.base_minima,
        activo=obj.activo, aplica_compra=obj.aplica_compra, aplica_venta=obj.aplica_venta,
        cuenta_compras_id=obj.cuenta_compras_id,
        cuenta_compras_codigo=cc, cuenta_compras_nombre=cn,
        cuenta_ventas_id=obj.cuenta_ventas_id,
        cuenta_ventas_codigo=vc, cuenta_ventas_nombre=vn,
    )


# ---------------------------------------------------------------------------
# Condiciones de pago
# ---------------------------------------------------------------------------

def listar_condiciones_pago(db: Session, solo_activas: bool = False):
    q = db.query(AdmCondicionPago)
    if solo_activas:
        q = q.filter(AdmCondicionPago.activo == True)
    return q.order_by(AdmCondicionPago.dias_vencimiento).all()


def crear_condicion_pago(db: Session, data: CondicionPagoCreate, actor: UsuarioActual):
    if db.query(AdmCondicionPago).filter(AdmCondicionPago.codigo == data.codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe una condición con ese código")
    obj = AdmCondicionPago(**data.model_dump(), creado_por=uuid.UUID(actor.id))
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def actualizar_condicion_pago(db: Session, id: uuid.UUID, data: CondicionPagoUpdate, actor: UsuarioActual):
    obj = db.query(AdmCondicionPago).filter(AdmCondicionPago.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    if data.codigo and data.codigo != obj.codigo:
        if db.query(AdmCondicionPago).filter(AdmCondicionPago.codigo == data.codigo, AdmCondicionPago.id != id).first():
            raise HTTPException(status_code=400, detail="Ya existe una condición con ese código")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return obj


# ---------------------------------------------------------------------------
# Tarifas IVA
# ---------------------------------------------------------------------------

def listar_tarifas_iva(db: Session, solo_activas: bool = False):
    q = db.query(AdmTarifaIva)
    if solo_activas:
        q = q.filter(AdmTarifaIva.activo == True)
    return [_enrich_iva(db, o) for o in q.order_by(AdmTarifaIva.tipo, AdmTarifaIva.porcentaje.desc()).all()]


def crear_tarifa_iva(db: Session, data: TarifaIvaCreate, actor: UsuarioActual):
    obj = AdmTarifaIva(**data.model_dump(), creado_por=uuid.UUID(actor.id))
    db.add(obj); db.commit(); db.refresh(obj)
    return _enrich_iva(db, obj)


def actualizar_tarifa_iva(db: Session, id: uuid.UUID, data: TarifaIvaUpdate, actor: UsuarioActual):
    obj = db.query(AdmTarifaIva).filter(AdmTarifaIva.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return _enrich_iva(db, obj)


# ---------------------------------------------------------------------------
# Retenciones
# ---------------------------------------------------------------------------

def listar_retenciones(db: Session, solo_activas: bool = False, tipo: str | None = None):
    q = db.query(AdmRetencion)
    if solo_activas:
        q = q.filter(AdmRetencion.activo == True)
    if tipo:
        q = q.filter(AdmRetencion.tipo == tipo)
    return [_enrich_ret(db, o) for o in q.order_by(AdmRetencion.tipo, AdmRetencion.porcentaje.desc()).all()]


def crear_retencion(db: Session, data: RetencionCreate, actor: UsuarioActual):
    obj = AdmRetencion(**data.model_dump(), creado_por=uuid.UUID(actor.id))
    db.add(obj); db.commit(); db.refresh(obj)
    return _enrich_ret(db, obj)


def actualizar_retencion(db: Session, id: uuid.UUID, data: RetencionUpdate, actor: UsuarioActual):
    obj = db.query(AdmRetencion).filter(AdmRetencion.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return _enrich_ret(db, obj)
