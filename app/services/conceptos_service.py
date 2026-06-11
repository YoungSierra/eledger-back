import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.admin import AdmConcepto, AdmConceptoRetencion, AdmTarifaIva, AdmRetencion
from app.models.contabilidad import CntCuenta
from app.schemas.auth import UsuarioActual
from app.schemas.conceptos import (
    ConceptoCreate, ConceptoUpdate, ConceptoResponse, ConceptoRetencionOut,
)


def _cuenta_info(db, cuenta_id):
    if not cuenta_id:
        return None, None
    c = db.query(CntCuenta).filter(CntCuenta.id == cuenta_id).first()
    return (c.codigo, c.nombre) if c else (None, None)


def _enrich(db: Session, obj: AdmConcepto) -> ConceptoResponse:
    iva = db.query(AdmTarifaIva).filter(AdmTarifaIva.id == obj.tarifa_iva_id).first() if obj.tarifa_iva_id else None
    iva_cta_compras_id = iva.cuenta_iva_compras_id if iva else None
    iva_cta_compras_codigo, _ = _cuenta_info(db, iva_cta_compras_id)
    gc, gn = _cuenta_info(db, obj.cuenta_gasto_id)
    cc, cn = _cuenta_info(db, obj.cuenta_cxp_id)

    retenciones_out = []
    for cr in obj.retenciones:
        ret = db.query(AdmRetencion).filter(AdmRetencion.id == cr.retencion_id).first()
        cta_compras_codigo = None
        if ret and ret.cuenta_compras_id:
            cta = db.get(CntCuenta, ret.cuenta_compras_id)
            cta_compras_codigo = cta.codigo if cta else None
        retenciones_out.append(ConceptoRetencionOut(
            id=cr.id, retencion_id=cr.retencion_id,
            retencion_nombre=ret.nombre if ret else None,
            retencion_tipo=ret.tipo if ret else None,
            retencion_porcentaje=ret.porcentaje if ret else None,
            retencion_cuenta_compras_id=ret.cuenta_compras_id if ret else None,
            retencion_cuenta_compras_codigo=cta_compras_codigo,
            activo=cr.activo,
        ))

    return ConceptoResponse(
        id=obj.id, codigo=obj.codigo, nombre=obj.nombre,
        modulo=obj.modulo, descripcion=obj.descripcion,
        tarifa_iva_id=obj.tarifa_iva_id,
        tarifa_iva_nombre=iva.nombre if iva else None,
        tarifa_iva_tipo=iva.tipo if iva else None,
        tarifa_iva_porcentaje=iva.porcentaje if iva else None,
        tarifa_iva_cuenta_compras_id=iva_cta_compras_id,
        tarifa_iva_cuenta_compras_codigo=iva_cta_compras_codigo,
        cuenta_gasto_id=obj.cuenta_gasto_id,
        cuenta_gasto_codigo=gc, cuenta_gasto_nombre=gn,
        cuenta_cxp_id=obj.cuenta_cxp_id,
        cuenta_cxp_codigo=cc, cuenta_cxp_nombre=cn,
        activo=obj.activo,
        retenciones=retenciones_out,
    )


def listar_conceptos(db: Session, modulo: str, solo_activos: bool = False) -> list[ConceptoResponse]:
    q = db.query(AdmConcepto).filter(AdmConcepto.modulo == modulo)
    if solo_activos:
        q = q.filter(AdmConcepto.activo == True)
    return [_enrich(db, o) for o in q.order_by(AdmConcepto.nombre).all()]


def crear_concepto(db: Session, modulo: str, data: ConceptoCreate, actor: UsuarioActual) -> ConceptoResponse:
    codigo = data.codigo.upper()
    if db.query(AdmConcepto).filter(AdmConcepto.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe un concepto con ese código")
    obj = AdmConcepto(
        codigo=codigo, nombre=data.nombre, modulo=modulo,
        descripcion=data.descripcion, tarifa_iva_id=data.tarifa_iva_id,
        cuenta_gasto_id=data.cuenta_gasto_id, cuenta_cxp_id=data.cuenta_cxp_id,
        activo=True, creado_por=uuid.UUID(actor.id),
    )
    db.add(obj); db.flush()
    for r in data.retenciones:
        db.add(AdmConceptoRetencion(concepto_id=obj.id, retencion_id=r.retencion_id, activo=True))
    db.commit(); db.refresh(obj)
    return _enrich(db, obj)


def actualizar_concepto(db: Session, id: uuid.UUID, data: ConceptoUpdate, actor: UsuarioActual) -> ConceptoResponse:
    obj = db.query(AdmConcepto).filter(AdmConcepto.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concepto no encontrado")
    for campo in ("nombre", "descripcion", "tarifa_iva_id", "cuenta_gasto_id", "cuenta_cxp_id", "activo"):
        valor = getattr(data, campo)
        if valor is not None:
            setattr(obj, campo, valor)
    if data.retenciones is not None:
        db.query(AdmConceptoRetencion).filter(AdmConceptoRetencion.concepto_id == id).delete()
        for r in data.retenciones:
            db.add(AdmConceptoRetencion(concepto_id=id, retencion_id=r.retencion_id, activo=True))
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return _enrich(db, obj)
