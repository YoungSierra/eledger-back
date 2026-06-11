import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contabilidad import CntCuenta
from app.schemas.auth import UsuarioActual
from app.schemas.cuentas import CuentaCreate, CuentaUpdate


def _nivel(codigo: str) -> int:
    n = len(codigo)
    if n == 1: return 1
    if n == 2: return 2
    if n <= 4: return 3
    if n <= 6: return 4
    return 5


def listar_cuentas(
    db: Session,
    padre_id: uuid.UUID | None = None,
    solo_activas: bool = True,
    busqueda: str | None = None,
    solo_movimiento: bool = False,
) -> list[CntCuenta]:
    q = db.query(CntCuenta)
    if solo_activas:
        q = q.filter(CntCuenta.activo == True)
    if solo_movimiento:
        q = q.filter(CntCuenta.acepta_movimiento == True)
        if busqueda:
            term = f"%{busqueda}%"
            q = q.filter((CntCuenta.codigo.ilike(term)) | (CntCuenta.nombre.ilike(term)))
        return q.order_by(CntCuenta.codigo).all()
    if padre_id is not None:
        q = q.filter(CntCuenta.padre_id == padre_id)
    elif padre_id is None and busqueda is None:
        q = q.filter(CntCuenta.padre_id.is_(None))
    if busqueda:
        term = f"%{busqueda}%"
        q = q.filter((CntCuenta.codigo.ilike(term)) | (CntCuenta.nombre.ilike(term)))
        return q.order_by(CntCuenta.codigo).limit(100).all()
    return q.order_by(CntCuenta.codigo).all()


def obtener_cuenta(db: Session, cuenta_id: uuid.UUID) -> CntCuenta:
    c = db.query(CntCuenta).filter(CntCuenta.id == cuenta_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    return c


def crear_cuenta(db: Session, data: CuentaCreate, actor: UsuarioActual) -> CntCuenta:
    existente = db.query(CntCuenta).filter(CntCuenta.codigo == data.codigo).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Ya existe la cuenta {data.codigo}")

    nivel = _nivel(data.codigo)
    acepta = len(data.codigo) >= 6

    if data.padre_id:
        padre = obtener_cuenta(db, data.padre_id)
        if not data.codigo.startswith(padre.codigo):
            raise HTTPException(
                status_code=400,
                detail=f"El código {data.codigo} no es hijo de {padre.codigo}",
            )

    cuenta = CntCuenta(
        codigo=data.codigo,
        nombre=data.nombre,
        nivel=nivel,
        naturaleza=data.naturaleza,
        acepta_movimiento=acepta,
        requiere_tercero=data.requiere_tercero,
        requiere_cc=data.requiere_cc,
        padre_id=data.padre_id,
        descripcion=data.descripcion,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(cuenta)
    db.commit()
    db.refresh(cuenta)
    return cuenta


def actualizar_cuenta(db: Session, cuenta_id: uuid.UUID, data: CuentaUpdate, actor: UsuarioActual) -> CntCuenta:
    c = obtener_cuenta(db, cuenta_id)
    if data.nombre is not None:
        c.nombre = data.nombre
    if data.descripcion is not None:
        c.descripcion = data.descripcion
    if data.acepta_movimiento is not None:
        c.acepta_movimiento = data.acepta_movimiento
    if data.requiere_tercero is not None:
        c.requiere_tercero = data.requiere_tercero
    if data.requiere_cc is not None:
        c.requiere_cc = data.requiere_cc
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


def reactivar_cuenta(db: Session, cuenta_id: uuid.UUID, actor: UsuarioActual) -> CntCuenta:
    c = db.query(CntCuenta).filter(CntCuenta.id == cuenta_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    c.activo = True
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


def desactivar_cuenta(db: Session, cuenta_id: uuid.UUID, actor: UsuarioActual) -> None:
    c = obtener_cuenta(db, cuenta_id)
    hijos = db.query(CntCuenta).filter(CntCuenta.padre_id == cuenta_id, CntCuenta.activo == True).count()
    if hijos:
        raise HTTPException(status_code=400, detail="No se puede desactivar una cuenta con subcuentas activas")
    c.activo = False
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()
