import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.contabilidad import CntCuenta
from app.models.cxc import CxcParametroContable
from app.models.cxp import CxpParametroContable
from app.schemas.auth import UsuarioActual
from app.schemas.parametros import (
    CxcParametroUpdate, CxcParametroResponse,
    CxpParametroUpdate, CxpParametroResponse,
)


def _display(db: Session, id: Optional[uuid.UUID]) -> Optional[str]:
    if not id:
        return None
    c = db.query(CntCuenta).filter(CntCuenta.id == id).first()
    return f"{c.codigo} — {c.nombre}" if c else None


def obtener_parametros_cxc(db: Session) -> CxcParametroResponse:
    obj = db.query(CxcParametroContable).first()
    if not obj:
        raise Exception("Parámetros CxC no inicializados")
    return CxcParametroResponse(
        id=obj.id,
        cuenta_clientes_id=obj.cuenta_clientes_id,
        cuenta_clientes_display=_display(db, obj.cuenta_clientes_id),
        cuenta_ingresos_id=obj.cuenta_ingresos_id,
        cuenta_ingresos_display=_display(db, obj.cuenta_ingresos_id),
        cuenta_iva_id=obj.cuenta_iva_id,
        cuenta_iva_display=_display(db, obj.cuenta_iva_id),
        cuenta_valores_terceros_id=obj.cuenta_valores_terceros_id,
        cuenta_valores_terceros_display=_display(db, obj.cuenta_valores_terceros_id),
        cuenta_anticipos_id=obj.cuenta_anticipos_id,
        cuenta_anticipos_display=_display(db, obj.cuenta_anticipos_id),
        cuenta_descuentos_id=obj.cuenta_descuentos_id,
        cuenta_descuentos_display=_display(db, obj.cuenta_descuentos_id),
        cuenta_aprovechamientos_id=obj.cuenta_aprovechamientos_id,
        cuenta_aprovechamientos_display=_display(db, obj.cuenta_aprovechamientos_id),
        cuenta_devolucion_venta_id=obj.cuenta_devolucion_venta_id,
        cuenta_devolucion_venta_display=_display(db, obj.cuenta_devolucion_venta_id),
    )


def actualizar_parametros_cxc(
    db: Session, data: CxcParametroUpdate, actor: UsuarioActual
) -> CxcParametroResponse:
    obj = db.query(CxcParametroContable).first()
    if not obj:
        raise Exception("Parámetros CxC no inicializados")
    for campo in ("cuenta_clientes_id", "cuenta_ingresos_id", "cuenta_iva_id", "cuenta_valores_terceros_id", "cuenta_anticipos_id", "cuenta_descuentos_id", "cuenta_aprovechamientos_id", "cuenta_devolucion_venta_id"):
        val = getattr(data, campo)
        if val is not None:
            setattr(obj, campo, val)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obtener_parametros_cxc(db)


def obtener_parametros_cxp(db: Session) -> CxpParametroResponse:
    obj = db.query(CxpParametroContable).first()
    if not obj:
        raise Exception("Parámetros CxP no inicializados")
    return CxpParametroResponse(
        id=obj.id,
        cuenta_proveedores_id=obj.cuenta_proveedores_id,
        cuenta_proveedores_display=_display(db, obj.cuenta_proveedores_id),
        cuenta_mercancias_recibidas_id=obj.cuenta_mercancias_recibidas_id,
        cuenta_mercancias_recibidas_display=_display(db, obj.cuenta_mercancias_recibidas_id),
        cuenta_anticipos_id=obj.cuenta_anticipos_id,
        cuenta_anticipos_display=_display(db, obj.cuenta_anticipos_id),
        cuenta_descuentos_id=obj.cuenta_descuentos_id,
        cuenta_descuentos_display=_display(db, obj.cuenta_descuentos_id),
        cuenta_aprovechamientos_id=obj.cuenta_aprovechamientos_id,
        cuenta_aprovechamientos_display=_display(db, obj.cuenta_aprovechamientos_id),
    )


def actualizar_parametros_cxp(
    db: Session, data: CxpParametroUpdate, actor: UsuarioActual
) -> CxpParametroResponse:
    obj = db.query(CxpParametroContable).first()
    if not obj:
        raise Exception("Parámetros CxP no inicializados")
    for campo in ("cuenta_proveedores_id", "cuenta_mercancias_recibidas_id",
                  "cuenta_anticipos_id", "cuenta_descuentos_id", "cuenta_aprovechamientos_id"):
        val = getattr(data, campo)
        if val is not None:
            setattr(obj, campo, val)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obtener_parametros_cxp(db)
