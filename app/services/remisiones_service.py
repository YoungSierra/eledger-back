from datetime import date, datetime as _dt
from decimal import Decimal
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.adm import AdmTercero
from app.models.admin import AdmMoneda
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntPeriodo
from app.models.inventario import (
    InvBodega, InvMovimiento, InvMovimientoLinea,
    InvProducto, InvProductoBodega, InvRemision, InvRemisionLinea, InvUnidadMedida,
)
from app.models.admin import AdmTipoDocumento, AdmConsecutivo
from app.schemas.auth import UsuarioActual
from app.schemas.remisiones import (
    RemisionCreate, RemisionDetalle, RemisionLinea as RemisionLineaSchema,
    RemisionListItem, RemisionListResponse,
)
from app.services.inventario_service import (
    _buscar_periodo_inv, _resolver_cuenta_inventario_inv,
    _resolver_cuenta_ajuste,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generar_numero_rem(db: Session) -> str:
    td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "RM").first()
    if not td:
        raise HTTPException(500, "Tipo de documento RM no configurado")
    cons = db.query(AdmConsecutivo).filter(
        AdmConsecutivo.tipo_documento_id == td.id
    ).with_for_update().first()
    if not cons:
        raise HTTPException(500, "Consecutivo REM no configurado")
    siguiente = cons.numero_actual + 1
    cons.numero_actual = siguiente
    prefijo = cons.prefijo or "REM-"
    longitud = cons.longitud_minima or 4
    return f"{prefijo}{str(siguiente).zfill(longitud)}"


def _calcular_cantidad_base(db: Session, producto_id: uuid.UUID, um_id: uuid.UUID, cantidad: Decimal) -> Decimal:
    from app.models.inventario import InvProductoUm
    prod = db.get(InvProducto, producto_id)
    if not prod:
        return cantidad
    if prod.um_base_id == um_id:
        return cantidad
    pu = db.query(InvProductoUm).filter(
        InvProductoUm.producto_id == producto_id,
        InvProductoUm.um_id == um_id,
    ).first()
    if pu:
        return cantidad * pu.factor
    return cantidad


def _to_detalle(db: Session, rem: InvRemision) -> RemisionDetalle:
    cliente = db.get(AdmTercero, rem.cliente_id)
    bodega = db.get(InvBodega, rem.bodega_id)
    lineas = []
    for l in rem.lineas:
        prod = db.get(InvProducto, l.producto_id)
        um = db.get(InvUnidadMedida, l.um_id)
        lineas.append(RemisionLineaSchema(
            id=l.id,
            producto_id=l.producto_id,
            producto_codigo=prod.codigo if prod else "",
            producto_nombre=prod.nombre if prod else "",
            cantidad=l.cantidad,
            um_id=l.um_id,
            um_codigo=um.codigo if um else "",
            costo_unitario=l.costo_unitario,
        ))
    return RemisionDetalle(
        id=rem.id,
        numero=rem.numero,
        fecha=rem.fecha.strftime("%Y-%m-%d") if rem.fecha else "",
        cliente_id=rem.cliente_id,
        cliente_nombre=cliente.razon_social if cliente else "",
        cliente_nit=cliente.nit if cliente else None,
        bodega_id=rem.bodega_id,
        bodega_nombre=bodega.nombre if bodega else "",
        notas=rem.notas,
        estado=rem.estado,
        movimiento_id=rem.movimiento_id,
        asiento_id=rem.asiento_id,
        lineas=lineas,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def listar_remisiones(
    db: Session,
    pagina: int = 1,
    por_pagina: int = 30,
    estado: Optional[str] = None,
    cliente_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    sin_facturar: bool = False,
) -> RemisionListResponse:
    q = db.query(InvRemision).filter(InvRemision.activo == True)
    if estado:
        q = q.filter(InvRemision.estado == estado)
    if cliente_id:
        q = q.filter(InvRemision.cliente_id == cliente_id)
    if fecha_desde:
        q = q.filter(InvRemision.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(InvRemision.fecha <= fecha_hasta)
    if sin_facturar:
        q = q.filter(InvRemision.estado == "despachada")
    total = q.count()
    items_raw = q.order_by(InvRemision.fecha.desc(), InvRemision.creado_en.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    items = []
    for r in items_raw:
        cliente = db.get(AdmTercero, r.cliente_id)
        bodega = db.get(InvBodega, r.bodega_id)
        num_lineas = db.query(InvRemisionLinea).filter(InvRemisionLinea.remision_id == r.id).count()
        items.append(RemisionListItem(
            id=r.id,
            numero=r.numero,
            fecha=r.fecha.strftime("%Y-%m-%d") if r.fecha else "",
            cliente_id=r.cliente_id,
            cliente_nombre=cliente.razon_social if cliente else "",
            cliente_nit=cliente.nit if cliente else None,
            bodega_id=r.bodega_id,
            bodega_nombre=bodega.nombre if bodega else "",
            estado=r.estado,
            num_lineas=num_lineas,
        ))
    return RemisionListResponse(items=items, total=total, pagina=pagina, por_pagina=por_pagina)


def obtener_remision(db: Session, remision_id: uuid.UUID) -> RemisionDetalle:
    rem = db.get(InvRemision, remision_id)
    if not rem or not rem.activo:
        raise HTTPException(404, "Remisión no encontrada")
    return _to_detalle(db, rem)


def crear_remision(db: Session, data: RemisionCreate, actor: UsuarioActual) -> RemisionDetalle:
    periodo = _buscar_periodo_inv(db, data.fecha)
    numero = _generar_numero_rem(db)
    fecha_dt = _dt.combine(data.fecha, _dt.min.time())

    rem = InvRemision(
        numero=numero,
        fecha=fecha_dt,
        periodo_id=periodo.id,
        cliente_id=data.cliente_id,
        bodega_id=data.bodega_id,
        cotizacion_id=data.cotizacion_id,
        notas=data.notas,
        estado="borrador",
        creado_por=actor.id,
    )
    db.add(rem)
    db.flush()

    for l in data.lineas:
        cantidad_base = _calcular_cantidad_base(db, l.producto_id, l.um_id, l.cantidad)
        db.add(InvRemisionLinea(
            remision_id=rem.id,
            producto_id=l.producto_id,
            cantidad=l.cantidad,
            um_id=l.um_id,
            cantidad_base=cantidad_base,
            costo_unitario=Decimal("0"),
        ))

    db.commit()
    db.refresh(rem)
    return _to_detalle(db, rem)


def editar_remision(db: Session, remision_id: uuid.UUID, data: RemisionCreate, actor: UsuarioActual) -> RemisionDetalle:
    rem = db.get(InvRemision, remision_id)
    if not rem or not rem.activo:
        raise HTTPException(404, "Remisión no encontrada")
    if rem.estado != "borrador":
        raise HTTPException(400, "Solo se pueden editar remisiones en borrador")

    periodo = _buscar_periodo_inv(db, data.fecha)
    fecha_dt = _dt.combine(data.fecha, _dt.min.time())

    db.query(InvRemisionLinea).filter(InvRemisionLinea.remision_id == rem.id).delete()
    rem.fecha = fecha_dt
    rem.periodo_id = periodo.id
    rem.cliente_id = data.cliente_id
    rem.bodega_id = data.bodega_id
    rem.cotizacion_id = data.cotizacion_id
    rem.notas = data.notas
    db.flush()

    for l in data.lineas:
        cantidad_base = _calcular_cantidad_base(db, l.producto_id, l.um_id, l.cantidad)
        db.add(InvRemisionLinea(
            remision_id=rem.id,
            producto_id=l.producto_id,
            cantidad=l.cantidad,
            um_id=l.um_id,
            cantidad_base=cantidad_base,
            costo_unitario=Decimal("0"),
        ))

    db.commit()
    db.refresh(rem)
    return _to_detalle(db, rem)


def despachar_remision(db: Session, remision_id: uuid.UUID, actor: UsuarioActual) -> RemisionDetalle:
    rem = db.get(InvRemision, remision_id)
    if not rem or not rem.activo:
        raise HTTPException(404, "Remisión no encontrada")
    if rem.estado != "borrador":
        raise HTTPException(400, f"La remisión ya está en estado '{rem.estado}'")

    db.expire(rem)
    lineas = db.query(InvRemisionLinea).filter(InvRemisionLinea.remision_id == rem.id).all()
    if not lineas:
        raise HTTPException(400, "La remisión no tiene líneas")

    periodo = db.get(CntPeriodo, rem.periodo_id)
    fecha = rem.fecha.date() if hasattr(rem.fecha, "date") else rem.fecha

    # Crear inv_movimiento SALIDA_VENTA
    mov = InvMovimiento(
        tipo="SALIDA_VENTA",
        fecha=rem.fecha,
        periodo_id=rem.periodo_id,
        bodega_id=rem.bodega_id,
        numero=rem.numero,
        descripcion=f"Remisión {rem.numero}",
        estado="borrador",
        origen_tipo="inv_remision",
        origen_id=rem.id,
        creado_por=actor.id,
    )
    db.add(mov)
    db.flush()

    costo_total_mov = Decimal("0")
    lineas_mov = []

    for l in lineas:
        prod = db.get(InvProducto, l.producto_id)
        if not prod or not prod.maneja_inventario:
            continue

        pb = db.query(InvProductoBodega).filter(
            InvProductoBodega.producto_id == l.producto_id,
            InvProductoBodega.bodega_id == rem.bodega_id,
        ).first()

        costo_unit = pb.costo_promedio if pb and pb.costo_promedio > 0 else Decimal("0")
        costo_total = (l.cantidad_base * costo_unit).quantize(Decimal("0.0001"))

        # Actualizar stock
        if pb:
            if pb.cantidad < l.cantidad_base:
                raise HTTPException(400, f"Stock insuficiente para {prod.nombre}: disponible {pb.cantidad}, requerido {l.cantidad_base}")
            pb.cantidad -= l.cantidad_base
        else:
            raise HTTPException(400, f"Sin stock registrado para {prod.nombre} en la bodega")

        # Línea movimiento
        mov_lin = InvMovimientoLinea(
            movimiento_id=mov.id,
            producto_id=l.producto_id,
            cantidad=l.cantidad,
            um_id=l.um_id,
            cantidad_base=l.cantidad_base,
            costo_unitario=costo_unit,
            costo_total=costo_total,
        )
        db.add(mov_lin)
        lineas_mov.append((l, costo_unit, costo_total))

        # Actualizar costo en línea de remisión
        l.costo_unitario = costo_unit
        costo_total_mov += costo_total

    # Confirmar movimiento
    mov.estado = "confirmado"
    rem.movimiento_id = mov.id

    # Asiento de costo de ventas
    moneda_func = db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.activo == True).first()
    if moneda_func and costo_total_mov > 0:
        td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "RM").first()
        asiento = CntAsiento(
            tipo_documento_id=td.id if td else None,
            documento_numero=rem.numero,
            fecha=fecha,
            periodo_id=rem.periodo_id,
            descripcion=f"Costo de ventas — {rem.numero}",
            estado="publicado",
            moneda_id=moneda_func.id,
            documento_origen_id=rem.id,
            documento_origen_tipo="inv_remision",
            creado_por=actor.id,
        )
        db.add(asiento)
        db.flush()
        rem.asiento_id = asiento.id

        orden = 1
        for l, costo_unit, costo_total in lineas_mov:
            if costo_total == 0:
                continue
            prod = db.get(InvProducto, l.producto_id)
            cuenta_costo = _resolver_cuenta_ajuste(db, prod, "cuenta_costo_ventas_id")
            cuenta_inv = _resolver_cuenta_inventario_inv(db, prod)
            if not cuenta_costo or not cuenta_inv:
                continue
            # Déb. Costo de ventas / Cred. Inventario
            db.add(CntAsientoLinea(
                asiento_id=asiento.id, orden=orden,
                cuenta_id=cuenta_costo.id,
                descripcion=f"Costo ventas {prod.nombre}",
                debito=costo_total, credito=Decimal("0"),
                debito_funcional=costo_total, credito_funcional=Decimal("0"),
            ))
            orden += 1
            db.add(CntAsientoLinea(
                asiento_id=asiento.id, orden=orden,
                cuenta_id=cuenta_inv.id,
                descripcion=f"Costo ventas {prod.nombre}",
                debito=Decimal("0"), credito=costo_total,
                debito_funcional=Decimal("0"), credito_funcional=costo_total,
            ))
            orden += 1

    rem.estado = "despachada"
    db.commit()
    db.refresh(rem)
    return _to_detalle(db, rem)
