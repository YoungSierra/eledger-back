import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.bancos import BanBanco, BanCuenta, BanChequera
from app.models.admin import AdmMoneda
from app.models.contabilidad import CntCuenta
from app.schemas.auth import UsuarioActual
from app.schemas.bancos import (
    BancoCreate, BancoUpdate, BancoResponse,
    CuentaBancariaCreate, CuentaBancariaUpdate, CuentaBancariaResponse,
    ChequerapCreate, ChequeraUpdate, ChequeraResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enrich_cuenta(db: Session, obj: BanCuenta) -> CuentaBancariaResponse:
    banco = db.query(BanBanco).filter(BanBanco.id == obj.banco_id).first()
    moneda = db.query(AdmMoneda).filter(AdmMoneda.id == obj.moneda_id).first() if obj.moneda_id else None
    cuenta = db.query(CntCuenta).filter(CntCuenta.id == obj.cuenta_contable_id).first() if obj.cuenta_contable_id else None
    return CuentaBancariaResponse(
        id=obj.id, banco_id=obj.banco_id,
        banco_nombre=banco.nombre if banco else None,
        nombre=obj.nombre, numero=obj.numero, tipo=obj.tipo,
        moneda_id=obj.moneda_id,
        moneda_codigo=moneda.codigo if moneda else None,
        cuenta_contable_id=obj.cuenta_contable_id,
        cuenta_contable_codigo=cuenta.codigo if cuenta else None,
        cuenta_contable_nombre=cuenta.nombre if cuenta else None,
        saldo_inicial=obj.saldo_inicial,
        activo=obj.activo,
    )


# ---------------------------------------------------------------------------
# Bancos
# ---------------------------------------------------------------------------

def listar_bancos(db: Session, solo_activos: bool = False) -> list[BanBanco]:
    q = db.query(BanBanco)
    if solo_activos:
        q = q.filter(BanBanco.activo == True)
    return q.order_by(BanBanco.nombre).all()


def crear_banco(db: Session, data: BancoCreate, actor: UsuarioActual) -> BanBanco:
    obj = BanBanco(**data.model_dump(), creado_por=uuid.UUID(actor.id))
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def actualizar_banco(db: Session, id: uuid.UUID, data: BancoUpdate, actor: UsuarioActual) -> BanBanco:
    obj = db.query(BanBanco).filter(BanBanco.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banco no encontrado")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return obj


# ---------------------------------------------------------------------------
# Cuentas bancarias
# ---------------------------------------------------------------------------

def listar_cuentas(db: Session, solo_activas: bool = False) -> list[CuentaBancariaResponse]:
    q = db.query(BanCuenta)
    if solo_activas:
        q = q.filter(BanCuenta.activo == True)
    return [_enrich_cuenta(db, o) for o in q.order_by(BanCuenta.nombre).all()]


def crear_cuenta(db: Session, data: CuentaBancariaCreate, actor: UsuarioActual) -> CuentaBancariaResponse:
    if not db.query(BanBanco).filter(BanBanco.id == data.banco_id).first():
        raise HTTPException(status_code=400, detail="Banco no encontrado")
    obj = BanCuenta(**data.model_dump(), creado_por=uuid.UUID(actor.id))
    db.add(obj); db.commit(); db.refresh(obj)
    return _enrich_cuenta(db, obj)


def actualizar_cuenta(db: Session, id: uuid.UUID, data: CuentaBancariaUpdate, actor: UsuarioActual) -> CuentaBancariaResponse:
    obj = db.query(BanCuenta).filter(BanCuenta.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return _enrich_cuenta(db, obj)


# ---------------------------------------------------------------------------
# Chequeras
# ---------------------------------------------------------------------------

def _enrich_chequera(db: Session, obj: BanChequera) -> ChequeraResponse:
    cuenta = db.query(BanCuenta).filter(BanCuenta.id == obj.cuenta_id).first()
    banco = db.query(BanBanco).filter(BanBanco.id == cuenta.banco_id).first() if cuenta else None
    return ChequeraResponse(
        id=obj.id, cuenta_id=obj.cuenta_id,
        cuenta_nombre=f"{cuenta.nombre} ({cuenta.numero})" if cuenta else None,
        banco_nombre=banco.nombre if banco else None,
        prefijo=obj.prefijo, numero_desde=obj.numero_desde,
        numero_hasta=obj.numero_hasta, consecutivo_actual=obj.consecutivo_actual,
        estado=obj.estado, descripcion=obj.descripcion, activo=obj.activo,
    )


def listar_chequeras(db: Session, solo_activas: bool = False) -> list[ChequeraResponse]:
    q = db.query(BanChequera)
    if solo_activas:
        q = q.filter(BanChequera.activo == True)
    return [_enrich_chequera(db, o) for o in q.order_by(BanChequera.numero_desde).all()]


def crear_chequera(db: Session, data: ChequerapCreate, actor: UsuarioActual) -> ChequeraResponse:
    if not db.query(BanCuenta).filter(BanCuenta.id == data.cuenta_id).first():
        raise HTTPException(status_code=400, detail="Cuenta bancaria no encontrada")
    if data.numero_hasta < data.numero_desde:
        raise HTTPException(status_code=400, detail="numero_hasta debe ser >= numero_desde")
    obj = BanChequera(
        **data.model_dump(),
        consecutivo_actual=data.numero_desde,
        estado="ACTIVA",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return _enrich_chequera(db, obj)


def actualizar_chequera(db: Session, id: uuid.UUID, data: ChequeraUpdate, actor: UsuarioActual) -> ChequeraResponse:
    obj = db.query(BanChequera).filter(BanChequera.id == id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chequera no encontrada")
    payload = data.model_dump(exclude_unset=True)
    nd = payload.get("numero_desde", obj.numero_desde)
    nh = payload.get("numero_hasta", obj.numero_hasta)
    if nh < nd:
        raise HTTPException(status_code=400, detail="numero_hasta debe ser >= numero_desde")
    for campo, valor in payload.items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return _enrich_chequera(db, obj)
