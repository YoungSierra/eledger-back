"""Confirmación de la operación sobre lo cotizado.

Comercial cotiza, operación confirma lo que realmente se ejecutó. Solo lo
confirmado es facturable: sin este paso la factura saldría contra valores que
nadie verificó.

La cotización no se muta — lo confirmado vive en `ope_confirmacion_linea`, así
queda el rastro de lo cotizado contra lo ejecutado.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.auditoria import registrar as audit
from app.models.adm import AdmTercero
from app.models.admin import AdmUsuario
from app.models.ope import (
    OpeConfirmacionLinea, OpeCotizacion, OpeCotizacionLinea, OpeOperacion,
    orden_seccion,
)
from app.schemas.auth import UsuarioActual
from app.schemas.ope import (
    OpeAplicarPesoRequest,
    OpeConfirmacionCotizacionGrupo,
    OpeConfirmacionGuardarRequest,
    OpeConfirmacionLineaItem,
    OpeConfirmacionResponse,
)
from app.services.ope_cotizacion_service import _calcular_totales_linea

TOL = Decimal("0.0001")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _facturado(db: Session, cotizacion_id: uuid.UUID) -> dict:
    # Import local: facturacion_service importa este módulo para el bloqueo.
    from app.services.facturacion_service import _facturado_por_linea

    return _facturado_por_linea(db, cotizacion_id)


def _obtener_operacion(db: Session, operacion_id: uuid.UUID) -> OpeOperacion:
    op = db.query(OpeOperacion).filter(
        OpeOperacion.id == operacion_id,
        OpeOperacion.activo == True,
    ).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operación no encontrada")
    return op


def _confirmaciones_por_linea(db: Session, operacion_id: uuid.UUID) -> dict:
    filas = db.query(OpeConfirmacionLinea).filter(
        OpeConfirmacionLinea.operacion_id == operacion_id,
        OpeConfirmacionLinea.activo == True,
    ).all()
    return {f.cotizacion_linea_id: f for f in filas}


def _recalcular(cot: OpeCotizacion, linea: OpeCotizacionLinea, conf: OpeConfirmacionLinea) -> None:
    """Recalcula los totales confirmados con los valores que capturó operación.

    En POR_KG manda `base_confirmada` (el peso real). PORCENTAJE sigue saliendo
    del CIF cotizado — el CIF no es confirmable, solo el porcentaje.
    """
    tv, tc = _calcular_totales_linea(
        linea.tipo_calculo,
        Decimal(str(conf.valor_unitario_confirmado)),
        Decimal(str(conf.costo_unitario_confirmado)),
        Decimal(str(conf.base_confirmada)),
        Decimal(str(linea.minimo)) if linea.minimo is not None else None,
        cot.valor_cif or cot.valor_mercancia,
        cot.moneda_mercancia,
        linea.moneda,
        cot.trm,
        Decimal(str(linea.minimo_costo)) if linea.minimo_costo is not None else None,
    )
    conf.total_venta_confirmado = tv
    conf.total_costo_confirmado = tc


def _nueva_confirmacion(
    operacion_id: uuid.UUID, linea: OpeCotizacionLinea, actor_id: uuid.UUID
) -> OpeConfirmacionLinea:
    """Fila nueva precargada con lo cotizado — operación ajusta desde ahí."""
    return OpeConfirmacionLinea(
        operacion_id=operacion_id,
        cotizacion_linea_id=linea.id,
        confirmado=False,
        base_confirmada=linea.base,
        valor_unitario_confirmado=linea.valor_unitario,
        costo_unitario_confirmado=linea.costo_unitario,
        total_venta_confirmado=linea.total_venta,
        total_costo_confirmado=linea.total_costo,
        creado_por=actor_id,
    )


# ---------------------------------------------------------------------------
# Consulta
# ---------------------------------------------------------------------------

def obtener_confirmacion(db: Session, operacion_id: uuid.UUID) -> OpeConfirmacionResponse:
    op = _obtener_operacion(db, operacion_id)
    confs = _confirmaciones_por_linea(db, operacion_id)

    grupos: list[OpeConfirmacionCotizacionGrupo] = []
    total_lineas = confirmadas = 0

    for cot in sorted(op.cotizaciones, key=lambda c: c.numero):
        if not cot.activo:
            continue
        cliente = db.get(AdmTercero, cot.cliente_id)
        facturado = _facturado(db, cot.id)
        items: list[OpeConfirmacionLineaItem] = []

        for linea in sorted(cot.lineas, key=lambda l: (orden_seccion(l.seccion), l.orden)):
            conf = confs.get(linea.id)
            fact = facturado.get(linea.id, Decimal("0"))
            nombre = None
            if conf and conf.confirmado_por:
                u = db.get(AdmUsuario, conf.confirmado_por)
                nombre = f"{u.nombre} {u.apellido}" if u else None

            total_lineas += 1
            if conf and conf.confirmado:
                confirmadas += 1

            items.append(OpeConfirmacionLineaItem(
                cotizacion_linea_id=linea.id,
                seccion=linea.seccion,
                orden=linea.orden,
                descripcion=linea.descripcion,
                tipo_calculo=linea.tipo_calculo,
                moneda=linea.moneda,
                opcional=linea.opcional,
                valor_tercero=linea.valor_tercero,
                base_cotizada=linea.base,
                valor_unitario_cotizado=linea.valor_unitario,
                costo_unitario_cotizado=linea.costo_unitario,
                minimo=linea.minimo,
                minimo_costo=linea.minimo_costo,
                total_venta_cotizado=linea.total_venta,
                total_costo_cotizado=linea.total_costo,
                confirmado=conf.confirmado if conf else False,
                base_confirmada=conf.base_confirmada if conf else linea.base,
                valor_unitario_confirmado=conf.valor_unitario_confirmado if conf else linea.valor_unitario,
                costo_unitario_confirmado=conf.costo_unitario_confirmado if conf else linea.costo_unitario,
                total_venta_confirmado=conf.total_venta_confirmado if conf else linea.total_venta,
                total_costo_confirmado=conf.total_costo_confirmado if conf else linea.total_costo,
                confirmado_por_nombre=nombre,
                confirmado_en=conf.confirmado_en if conf else None,
                notas_confirmacion=conf.notas if conf else None,
                facturado=fact,
                bloqueada=fact > TOL,
            ))

        grupos.append(OpeConfirmacionCotizacionGrupo(
            cotizacion_id=cot.id,
            numero=cot.numero,
            cliente_nombre=cliente.razon_social if cliente else "",
            moneda_mercancia=cot.moneda_mercancia,
            trm=cot.trm,
            peso_kg=cot.peso_kg,
            lineas=items,
        ))

    return OpeConfirmacionResponse(
        operacion_id=op.id,
        numero=op.numero,
        total_lineas=total_lineas,
        lineas_confirmadas=confirmadas,
        cotizaciones=grupos,
    )


# ---------------------------------------------------------------------------
# Guardar
# ---------------------------------------------------------------------------

def guardar_confirmacion(
    db: Session, operacion_id: uuid.UUID, data: OpeConfirmacionGuardarRequest, actor: UsuarioActual
) -> OpeConfirmacionResponse:
    op = _obtener_operacion(db, operacion_id)
    actor_id = uuid.UUID(actor.id)
    ahora = datetime.now(timezone.utc)

    lineas_op = {}
    for cot in op.cotizaciones:
        for linea in cot.lineas:
            lineas_op[linea.id] = (cot, linea)

    confs = _confirmaciones_por_linea(db, operacion_id)
    tocadas = 0

    for item in data.lineas:
        par = lineas_op.get(item.cotizacion_linea_id)
        if not par:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Una línea no pertenece a las cotizaciones de esta operación",
            )
        cot, linea = par

        facturado = _facturado(db, cot.id).get(linea.id, Decimal("0"))
        if facturado > TOL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{linea.descripcion}' ya tiene facturación y no se puede ajustar.",
            )

        conf = confs.get(linea.id)
        if not conf:
            conf = _nueva_confirmacion(operacion_id, linea, actor_id)
            db.add(conf)
            confs[linea.id] = conf

        if item.base_confirmada is not None:
            conf.base_confirmada = item.base_confirmada
        if item.valor_unitario_confirmado is not None:
            conf.valor_unitario_confirmado = item.valor_unitario_confirmado
        if item.costo_unitario_confirmado is not None:
            conf.costo_unitario_confirmado = item.costo_unitario_confirmado
        if item.notas is not None:
            conf.notas = item.notas or None

        _recalcular(cot, linea, conf)

        if item.confirmado and not conf.confirmado:
            conf.confirmado_por = actor_id
            conf.confirmado_en = ahora
        elif not item.confirmado:
            conf.confirmado_por = None
            conf.confirmado_en = None
        conf.confirmado = item.confirmado

        conf.modificado_por = actor_id
        conf.modificado_en = ahora
        tocadas += 1

    db.flush()
    audit(db, "ope_confirmacion_linea", op.id, "UPDATE", actor_id,
          contexto={"operacion": op.numero, "lineas": tocadas})
    db.commit()
    return obtener_confirmacion(db, operacion_id)


def aplicar_peso(
    db: Session, operacion_id: uuid.UUID, data: OpeAplicarPesoRequest, actor: UsuarioActual
) -> OpeConfirmacionResponse:
    """Lleva un peso a todas las líneas POR_KG de una cotización de la operación.

    Evita teclear el mismo peso línea por línea cuando la operación pesó distinto
    a lo cotizado. Las líneas ya facturadas se saltan.
    """
    op = _obtener_operacion(db, operacion_id)
    actor_id = uuid.UUID(actor.id)
    ahora = datetime.now(timezone.utc)

    cot = next((c for c in op.cotizaciones if c.id == data.cotizacion_id), None)
    if not cot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cotización no pertenece a esta operación",
        )

    confs = _confirmaciones_por_linea(db, operacion_id)
    facturado = _facturado(db, cot.id)
    aplicadas = 0

    for linea in cot.lineas:
        if linea.tipo_calculo != "POR_KG":
            continue
        if facturado.get(linea.id, Decimal("0")) > TOL:
            continue
        conf = confs.get(linea.id)
        if not conf:
            conf = _nueva_confirmacion(operacion_id, linea, actor_id)
            db.add(conf)
            confs[linea.id] = conf
        conf.base_confirmada = data.peso_kg
        _recalcular(cot, linea, conf)
        conf.modificado_por = actor_id
        conf.modificado_en = ahora
        aplicadas += 1

    if aplicadas == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay líneas POR_KG ajustables en esta cotización",
        )

    db.flush()
    audit(db, "ope_confirmacion_linea", op.id, "UPDATE", actor_id,
          contexto={"operacion": op.numero, "accion": "aplicar_peso",
                    "cotizacion": cot.numero, "peso_kg": str(data.peso_kg), "lineas": aplicadas})
    db.commit()
    return obtener_confirmacion(db, operacion_id)


# ---------------------------------------------------------------------------
# Consumido por facturación
# ---------------------------------------------------------------------------

def sin_confirmar_obligatorias(db: Session, operacion_id: uuid.UUID) -> list[str]:
    """Conceptos NO opcionales que operación todavía no confirmó.

    Los opcionales quedan fuera a propósito: no confirmarlos es la forma de decir
    que no se ejecutaron, así que no deben trabar el cierre.
    """
    confirmadas = {
        f.cotizacion_linea_id
        for f in db.query(OpeConfirmacionLinea).filter(
            OpeConfirmacionLinea.operacion_id == operacion_id,
            OpeConfirmacionLinea.confirmado == True,
            OpeConfirmacionLinea.activo == True,
        ).all()
    }
    op = db.get(OpeOperacion, operacion_id)
    if not op:
        return []
    faltan: list[str] = []
    for cot in op.cotizaciones:
        if not cot.activo:
            continue
        for linea in sorted(cot.lineas, key=lambda l: (orden_seccion(l.seccion), l.orden)):
            if linea.opcional:
                continue
            if linea.id not in confirmadas:
                faltan.append(f"{cot.numero} · {linea.descripcion}")
    return faltan


def confirmadas_de_cotizacion(db: Session, cotizacion_id: uuid.UUID) -> dict:
    """{linea_id: total_venta_confirmado} de las líneas confirmadas.

    Vacío si la cotización no tiene operación: sin operación no hay confirmación
    y por lo tanto no hay nada facturable.
    """
    cot = db.get(OpeCotizacion, cotizacion_id)
    if not cot or not cot.operacion_id:
        return {}
    filas = (
        db.query(OpeConfirmacionLinea)
        .join(OpeCotizacionLinea, OpeCotizacionLinea.id == OpeConfirmacionLinea.cotizacion_linea_id)
        .filter(
            OpeConfirmacionLinea.operacion_id == cot.operacion_id,
            OpeConfirmacionLinea.confirmado == True,
            OpeConfirmacionLinea.activo == True,
            OpeCotizacionLinea.cotizacion_id == cotizacion_id,
        )
        .all()
    )
    return {f.cotizacion_linea_id: Decimal(str(f.total_venta_confirmado)) for f in filas}
