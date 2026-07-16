import uuid
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.admin import AdmConsecutivo, AdmMoneda, AdmTarifaIva, AdmTipoDocumento
from app.models.adm import AdmTercero
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntCuenta, CntPeriodo
from app.models.cxp import CxpParametroContable
from app.models.inventario import (
    InvBodega, InvMovimiento, InvMovimientoLinea,
    InvProducto, InvProductoBodega, InvTipoProducto, InvFamilia, InvUnidadMedida,
)
from app.models.compras import ComOrdenCompra, ComOcLinea, ComRecepcion, ComRecepcionLinea
from app.schemas.auth import UsuarioActual
from app.schemas.compras import (
    OcCreate, OcUpdate, OcResponse, OcListItem, OcListResponse, OcLineaResponse,
    RecepcionCreate, RecepcionUpdate, RecepcionResponse, RecepcionListItem,
    RecepcionListResponse, RecepcionLineaResponse,
)


# ─── Helpers comunes ─────────────────────────────────────────────────────────

def _buscar_periodo(db: Session, fecha: date) -> CntPeriodo:
    p = db.query(CntPeriodo).filter(
        CntPeriodo.fecha_inicio <= fecha,
        CntPeriodo.fecha_cierre >= fecha,
        CntPeriodo.estado == "abierto",
        CntPeriodo.activo == True,
    ).first()
    if not p:
        raise HTTPException(status_code=400, detail=f"No existe período contable abierto para la fecha {fecha}")
    return p


def _generar_numero(db: Session, codigo: str) -> str:
    td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == codigo).first()
    if not td:
        raise HTTPException(status_code=400, detail=f"Tipo de documento {codigo} no configurado")
    cons = (
        db.query(AdmConsecutivo)
        .filter(AdmConsecutivo.tipo_documento_id == td.id)
        .with_for_update()
        .first()
    )
    if not cons:
        raise HTTPException(status_code=400, detail=f"No hay consecutivo configurado para {codigo}")
    siguiente = max(cons.numero_actual + 1, cons.numero_inicio)
    cons.numero_actual = siguiente
    return f"{cons.prefijo or ''}{str(siguiente).zfill(cons.longitud_minima)}"


def _calcular_linea_oc(linea_in, factor: Decimal = Decimal("1")):
    """Retorna (cantidad_base, subtotal, total_iva, total)."""
    cantidad_base = linea_in.cantidad * factor
    base = linea_in.cantidad * linea_in.precio_unitario
    descuento = base * (linea_in.descuento_pct / 100)
    subtotal = base - descuento
    total_iva = subtotal * (linea_in.iva_pct / 100)
    total = subtotal + total_iva
    return cantidad_base, subtotal, total_iva, total


def _resolver_cuenta_inventario(db: Session, producto: InvProducto) -> CntCuenta | None:
    """Cascade: producto → familia → tipo_producto."""
    if producto.cuenta_inventario_id:
        return db.get(CntCuenta, producto.cuenta_inventario_id)
    if producto.familia_id:
        familia = db.get(InvFamilia, producto.familia_id)
        if familia and familia.cuenta_inventario_id:
            return db.get(CntCuenta, familia.cuenta_inventario_id)
    tipo = db.get(InvTipoProducto, producto.tipo_id)
    if tipo and tipo.cuenta_inventario_id:
        return db.get(CntCuenta, tipo.cuenta_inventario_id)
    return None


def _cuenta_proveedores(db: Session) -> CntCuenta | None:
    params = db.query(CxpParametroContable).first()
    if params and params.cuenta_proveedores_id:
        return db.get(CntCuenta, params.cuenta_proveedores_id)
    return None


def _cuenta_mercancias_recibidas(db: Session) -> CntCuenta | None:
    params = db.query(CxpParametroContable).first()
    if params and params.cuenta_mercancias_recibidas_id:
        return db.get(CntCuenta, params.cuenta_mercancias_recibidas_id)
    return None


# ─── Serialización ───────────────────────────────────────────────────────────

def _to_oc_linea_response(linea: ComOcLinea) -> OcLineaResponse:
    p = linea.producto
    cc = linea.centro_costo
    return OcLineaResponse(
        id=linea.id,
        producto_id=linea.producto_id,
        producto_codigo=p.codigo if p else None,
        producto_nombre=p.nombre if p else None,
        maneja_inventario=p.maneja_inventario if p else True,
        cantidad=linea.cantidad,
        um_id=linea.um_id,
        um_codigo=linea.um.codigo if linea.um else None,
        cantidad_base=linea.cantidad_base,
        precio_unitario=linea.precio_unitario,
        descuento_pct=linea.descuento_pct,
        subtotal=linea.subtotal,
        iva_pct=linea.iva_pct,
        total_iva=linea.total_iva,
        total=linea.total,
        tarifa_iva_id=linea.tarifa_iva_id,
        centro_costo_id=linea.centro_costo_id,
        centro_costo_codigo=cc.codigo if cc else None,
        centro_costo_nombre=cc.nombre if cc else None,
        cantidad_recibida=linea.cantidad_recibida,
        pendiente=linea.cantidad - linea.cantidad_recibida,
    )


def _to_oc_response(oc: ComOrdenCompra, recepciones_count: int = 0) -> OcResponse:
    p = oc.proveedor
    return OcResponse(
        id=oc.id,
        numero=oc.numero,
        fecha=oc.fecha,
        fecha_entrega_esperada=oc.fecha_entrega_esperada,
        periodo_id=oc.periodo_id,
        proveedor_id=oc.proveedor_id,
        proveedor_nit=p.nit if p else None,
        proveedor_nombre=p.razon_social if p else None,
        moneda_id=oc.moneda_id,
        moneda_codigo=oc.moneda.codigo if oc.moneda else None,
        trm=oc.trm,
        subtotal=oc.subtotal,
        total_iva=oc.total_iva,
        total=oc.total,
        notas=oc.notas,
        estado=oc.estado,
        creado_por=oc.creado_por,
        aprobado_por=oc.aprobado_por,
        aprobado_en=oc.aprobado_en,
        lineas=[_to_oc_linea_response(l) for l in oc.lineas],
    )


def _to_recepcion_linea_response(linea: ComRecepcionLinea) -> RecepcionLineaResponse:
    p = linea.producto
    return RecepcionLineaResponse(
        id=linea.id,
        oc_linea_id=linea.oc_linea_id,
        producto_id=linea.producto_id,
        producto_codigo=p.codigo if p else None,
        producto_nombre=p.nombre if p else None,
        maneja_inventario=p.maneja_inventario if p else True,
        cantidad=linea.cantidad,
        um_id=linea.um_id,
        um_codigo=linea.um.codigo if linea.um else None,
        cantidad_base=linea.cantidad_base,
        costo_unitario=linea.costo_unitario,
        costo_total=linea.cantidad_base * linea.costo_unitario,
    )


def _to_recepcion_response(rec: ComRecepcion) -> RecepcionResponse:
    p = rec.proveedor
    total_costo = sum(
        l.cantidad_base * l.costo_unitario for l in rec.lineas
    )
    return RecepcionResponse(
        id=rec.id,
        numero=rec.numero,
        fecha=rec.fecha,
        periodo_id=rec.periodo_id,
        oc_id=rec.oc_id,
        oc_numero=rec.oc.numero if rec.oc else None,
        bodega_id=rec.bodega_id,
        bodega_nombre=rec.bodega.nombre if rec.bodega else None,
        proveedor_id=rec.proveedor_id,
        proveedor_nit=p.nit if p else None,
        proveedor_nombre=p.razon_social if p else None,
        notas=rec.notas,
        estado=rec.estado,
        movimiento_id=rec.movimiento_id,
        asiento_id=rec.asiento_id,
        total_costo=total_costo,
        lineas=[_to_recepcion_linea_response(l) for l in rec.lineas],
    )


# ─── OC — CRUD ───────────────────────────────────────────────────────────────

def listar_ocs(
    db: Session, pagina: int = 1, por_pagina: int = 20,
    estado: list[str] | None = None, proveedor_id: uuid.UUID | None = None,
    busqueda: str | None = None,
) -> OcListResponse:
    q = db.query(ComOrdenCompra).filter(ComOrdenCompra.activo == True)
    if estado:
        q = q.filter(ComOrdenCompra.estado.in_(estado))
    if proveedor_id:
        q = q.filter(ComOrdenCompra.proveedor_id == proveedor_id)
    if busqueda:
        term = f"%{busqueda}%"
        q = q.join(ComOrdenCompra.proveedor).filter(
            ComOrdenCompra.numero.ilike(term) |
            AdmTercero.razon_social.ilike(term) |
            AdmTercero.nit.ilike(term)
        )
    total = q.count()
    ocs = q.order_by(ComOrdenCompra.fecha.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    counts = {
        oc_id: cnt
        for oc_id, cnt in db.query(ComRecepcion.oc_id, func.count(ComRecepcion.id))
        .filter(ComRecepcion.activo == True)
        .group_by(ComRecepcion.oc_id)
        .all()
    }

    items = []
    for oc in ocs:
        p = oc.proveedor
        items.append(OcListItem(
            id=oc.id,
            numero=oc.numero,
            fecha=oc.fecha,
            proveedor_nit=p.nit if p else None,
            proveedor_nombre=p.razon_social if p else None,
            moneda_codigo=oc.moneda.codigo if oc.moneda else None,
            subtotal=oc.subtotal,
            total_iva=oc.total_iva,
            total=oc.total,
            estado=oc.estado,
            recepciones_count=counts.get(oc.id, 0),
        ))
    return OcListResponse(items=items, total=total, pagina=pagina, por_pagina=por_pagina)


def crear_oc(db: Session, data: OcCreate, actor: UsuarioActual) -> OcResponse:
    if not data.lineas:
        raise HTTPException(status_code=400, detail="La OC debe tener al menos una línea")
    periodo = _buscar_periodo(db, data.fecha)
    actor_id = uuid.UUID(actor.id)
    numero = _generar_numero(db, "OC")

    oc = ComOrdenCompra(
        numero=numero,
        fecha=data.fecha,
        fecha_entrega_esperada=data.fecha_entrega_esperada,
        periodo_id=periodo.id,
        proveedor_id=data.proveedor_id,
        moneda_id=data.moneda_id,
        trm=data.trm,
        notas=data.notas,
        estado="borrador",
        creado_por=actor_id,
    )
    db.add(oc)
    db.flush()

    subtotal_total = Decimal("0")
    iva_total = Decimal("0")
    for li in data.lineas:
        producto = db.get(InvProducto, li.producto_id)
        if not producto or not producto.activo:
            raise HTTPException(status_code=400, detail=f"Producto no encontrado: {li.producto_id}")
        um = db.get(InvUnidadMedida, li.um_id)
        if not um:
            raise HTTPException(status_code=400, detail=f"Unidad de medida no encontrada: {li.um_id}")
        # factor de conversión: si la UM base es la misma, factor = 1
        factor = Decimal("1")
        if li.um_id != producto.um_base_id:
            from app.models.inventario import InvProductoUm
            pu = db.query(InvProductoUm).filter(
                InvProductoUm.producto_id == li.producto_id,
                InvProductoUm.um_id == li.um_id,
                InvProductoUm.activo == True,
            ).first()
            factor = pu.factor if pu else Decimal("1")

        cantidad_base, subtotal, total_iva, total = _calcular_linea_oc(li, factor)
        subtotal_total += subtotal
        iva_total += total_iva

        db.add(ComOcLinea(
            oc_id=oc.id,
            producto_id=li.producto_id,
            cantidad=li.cantidad,
            um_id=li.um_id,
            cantidad_base=cantidad_base,
            precio_unitario=li.precio_unitario,
            descuento_pct=li.descuento_pct,
            subtotal=subtotal,
            iva_pct=li.iva_pct,
            total_iva=total_iva,
            total=total,
            tarifa_iva_id=li.tarifa_iva_id,
            centro_costo_id=li.centro_costo_id,
        ))

    oc.subtotal = subtotal_total
    oc.total_iva = iva_total
    oc.total = subtotal_total + iva_total
    db.commit()
    db.refresh(oc)
    return _to_oc_response(oc)


def obtener_oc(db: Session, oc_id: uuid.UUID) -> OcResponse:
    oc = db.query(ComOrdenCompra).filter(ComOrdenCompra.id == oc_id, ComOrdenCompra.activo == True).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    return _to_oc_response(oc)


def actualizar_oc(db: Session, oc_id: uuid.UUID, data: OcUpdate, actor: UsuarioActual) -> OcResponse:
    oc = db.query(ComOrdenCompra).filter(ComOrdenCompra.id == oc_id, ComOrdenCompra.activo == True).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    if oc.estado != "borrador":
        raise HTTPException(status_code=400, detail="Solo se pueden editar OC en borrador")

    actor_id = uuid.UUID(actor.id)
    ahora = datetime.now(timezone.utc)

    if data.fecha is not None:
        periodo = _buscar_periodo(db, data.fecha)
        oc.fecha = data.fecha
        oc.periodo_id = periodo.id
    if data.fecha_entrega_esperada is not None:
        oc.fecha_entrega_esperada = data.fecha_entrega_esperada
    if data.proveedor_id is not None:
        oc.proveedor_id = data.proveedor_id
    if data.moneda_id is not None:
        oc.moneda_id = data.moneda_id
    if data.trm is not None:
        oc.trm = data.trm
    if data.notas is not None:
        oc.notas = data.notas

    if data.lineas is not None:
        for l in oc.lineas:
            db.delete(l)
        db.flush()

        fecha_oc = oc.fecha
        subtotal_total = Decimal("0")
        iva_total = Decimal("0")
        for li in data.lineas:
            producto = db.get(InvProducto, li.producto_id)
            if not producto or not producto.activo:
                raise HTTPException(status_code=400, detail=f"Producto no encontrado: {li.producto_id}")
            factor = Decimal("1")
            if li.um_id != producto.um_base_id:
                from app.models.inventario import InvProductoUm
                pu = db.query(InvProductoUm).filter(
                    InvProductoUm.producto_id == li.producto_id,
                    InvProductoUm.um_id == li.um_id,
                    InvProductoUm.activo == True,
                ).first()
                factor = pu.factor if pu else Decimal("1")

            cantidad_base, subtotal, total_iva, total = _calcular_linea_oc(li, factor)
            subtotal_total += subtotal
            iva_total += total_iva
            db.add(ComOcLinea(
                oc_id=oc.id,
                producto_id=li.producto_id,
                cantidad=li.cantidad,
                um_id=li.um_id,
                cantidad_base=cantidad_base,
                precio_unitario=li.precio_unitario,
                descuento_pct=li.descuento_pct,
                subtotal=subtotal,
                iva_pct=li.iva_pct,
                total_iva=total_iva,
                total=total,
                tarifa_iva_id=li.tarifa_iva_id,
                centro_costo_id=li.centro_costo_id,
            ))
        oc.subtotal = subtotal_total
        oc.total_iva = iva_total
        oc.total = subtotal_total + iva_total

    oc.modificado_por = actor_id
    oc.modificado_en = ahora
    db.commit()
    db.refresh(oc)
    return _to_oc_response(oc)


def aprobar_oc(db: Session, oc_id: uuid.UUID, actor: UsuarioActual) -> OcResponse:
    oc = db.query(ComOrdenCompra).filter(ComOrdenCompra.id == oc_id, ComOrdenCompra.activo == True).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    if oc.estado != "borrador":
        raise HTTPException(status_code=400, detail=f"No se puede aprobar una OC en estado '{oc.estado}'")
    if not oc.lineas:
        raise HTTPException(status_code=400, detail="No se puede aprobar una OC sin líneas")

    actor_id = uuid.UUID(actor.id)
    oc.estado = "aprobada"
    oc.aprobado_por = actor_id
    oc.aprobado_en = datetime.now(timezone.utc)
    oc.modificado_por = actor_id
    oc.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(oc)
    return _to_oc_response(oc)


def anular_oc(db: Session, oc_id: uuid.UUID, actor: UsuarioActual) -> OcResponse:
    oc = db.query(ComOrdenCompra).filter(ComOrdenCompra.id == oc_id, ComOrdenCompra.activo == True).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    if oc.estado in ("anulada", "recibida_total"):
        raise HTTPException(status_code=400, detail=f"No se puede anular una OC en estado '{oc.estado}'")
    # No anular si tiene recepciones confirmadas
    tiene_recep = db.query(ComRecepcion).filter(
        ComRecepcion.oc_id == oc_id,
        ComRecepcion.estado == "confirmada",
        ComRecepcion.activo == True,
    ).first()
    if tiene_recep:
        raise HTTPException(status_code=400, detail="No se puede anular: la OC tiene recepciones confirmadas")

    actor_id = uuid.UUID(actor.id)
    oc.estado = "anulada"
    oc.modificado_por = actor_id
    oc.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(oc)
    return _to_oc_response(oc)


# ─── Recepción — CRUD ────────────────────────────────────────────────────────

def listar_recepciones(
    db: Session, pagina: int = 1, por_pagina: int = 20,
    estado: str | None = None, oc_id: uuid.UUID | None = None,
) -> RecepcionListResponse:
    q = db.query(ComRecepcion).filter(ComRecepcion.activo == True)
    if estado:
        q = q.filter(ComRecepcion.estado == estado)
    if oc_id:
        q = q.filter(ComRecepcion.oc_id == oc_id)
    total = q.count()
    recs = q.order_by(ComRecepcion.fecha.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    items = []
    for rec in recs:
        p = rec.proveedor
        total_costo = sum(l.cantidad_base * l.costo_unitario for l in rec.lineas)
        items.append(RecepcionListItem(
            id=rec.id,
            numero=rec.numero,
            fecha=rec.fecha,
            oc_numero=rec.oc.numero if rec.oc else None,
            bodega_nombre=rec.bodega.nombre if rec.bodega else None,
            proveedor_nit=p.nit if p else None,
            proveedor_nombre=p.razon_social if p else None,
            total_costo=total_costo,
            estado=rec.estado,
        ))
    return RecepcionListResponse(items=items, total=total, pagina=pagina, por_pagina=por_pagina)


def _pendiente_oc_linea(
    db: Session,
    oc_linea: "ComOcLinea",
    excluir_recepcion_id: uuid.UUID | None,
) -> Decimal:
    """Pendiente real = cantidad OC - confirmado - borradores de otros (excluye excluir_recepcion_id)."""
    q = db.query(func.coalesce(func.sum(ComRecepcionLinea.cantidad), Decimal("0"))) \
        .join(ComRecepcion, ComRecepcion.id == ComRecepcionLinea.recepcion_id) \
        .filter(
            ComRecepcionLinea.oc_linea_id == oc_linea.id,
            ComRecepcion.estado == "borrador",
            ComRecepcion.activo == True,
        )
    if excluir_recepcion_id:
        q = q.filter(ComRecepcion.id != excluir_recepcion_id)
    en_borrador = q.scalar() or Decimal("0")
    return oc_linea.cantidad - oc_linea.cantidad_recibida - en_borrador


def crear_recepcion(db: Session, data: RecepcionCreate, actor: UsuarioActual) -> RecepcionResponse:
    if not data.lineas:
        raise HTTPException(status_code=400, detail="La recepción debe tener al menos una línea")

    oc = db.query(ComOrdenCompra).filter(ComOrdenCompra.id == data.oc_id, ComOrdenCompra.activo == True).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    if oc.estado not in ("aprobada", "en_proceso"):
        raise HTTPException(status_code=400, detail=f"La OC está en estado '{oc.estado}' — debe estar aprobada o en proceso")

    periodo = _buscar_periodo(db, data.fecha)
    actor_id = uuid.UUID(actor.id)
    numero = _generar_numero(db, "RECP")

    # Validar líneas contra OC
    oc_lineas_map = {str(l.id): l for l in oc.lineas}
    for li in data.lineas:
        oc_linea = oc_lineas_map.get(str(li.oc_linea_id))
        if not oc_linea:
            raise HTTPException(status_code=400, detail=f"Línea de OC {li.oc_linea_id} no pertenece a esta OC")
        if not oc_linea.producto.maneja_inventario:
            raise HTTPException(
                status_code=400,
                detail=f"El producto '{oc_linea.producto.nombre}' es de tipo SERVICIO y no requiere recepción de inventario"
            )
        pendiente = _pendiente_oc_linea(db, oc_linea, excluir_recepcion_id=None)
        if li.cantidad > pendiente:
            raise HTTPException(
                status_code=400,
                detail=f"La cantidad {li.cantidad} supera el pendiente ({pendiente}) para el producto '{oc_linea.producto.nombre}'"
            )

    rec = ComRecepcion(
        numero=numero,
        fecha=data.fecha,
        periodo_id=periodo.id,
        oc_id=data.oc_id,
        bodega_id=data.bodega_id,
        proveedor_id=oc.proveedor_id,
        notas=data.notas,
        estado="borrador",
        creado_por=actor_id,
    )
    db.add(rec)
    db.flush()

    for li in data.lineas:
        oc_linea = oc_lineas_map[str(li.oc_linea_id)]
        db.add(ComRecepcionLinea(
            recepcion_id=rec.id,
            oc_linea_id=li.oc_linea_id,
            producto_id=oc_linea.producto_id,
            cantidad=li.cantidad,
            um_id=oc_linea.um_id,
            cantidad_base=li.cantidad * (oc_linea.cantidad_base / oc_linea.cantidad) if oc_linea.cantidad else li.cantidad,
            costo_unitario=li.costo_unitario,
        ))

    db.commit()
    db.refresh(rec)
    return _to_recepcion_response(rec)


def obtener_recepcion(db: Session, rec_id: uuid.UUID) -> RecepcionResponse:
    rec = db.query(ComRecepcion).filter(ComRecepcion.id == rec_id, ComRecepcion.activo == True).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    return _to_recepcion_response(rec)


def actualizar_recepcion(db: Session, rec_id: uuid.UUID, data: RecepcionUpdate, actor: UsuarioActual) -> RecepcionResponse:
    rec = db.query(ComRecepcion).filter(ComRecepcion.id == rec_id, ComRecepcion.activo == True).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    if rec.estado != "borrador":
        raise HTTPException(status_code=400, detail="Solo se pueden editar recepciones en borrador")

    actor_id = uuid.UUID(actor.id)
    if data.fecha is not None:
        periodo = _buscar_periodo(db, data.fecha)
        rec.fecha = data.fecha
        rec.periodo_id = periodo.id
    if data.bodega_id is not None:
        rec.bodega_id = data.bodega_id
    if data.notas is not None:
        rec.notas = data.notas

    if data.lineas is not None:
        for l in rec.lineas:
            db.delete(l)
        db.flush()

        oc = db.get(ComOrdenCompra, rec.oc_id)
        oc_lineas_map = {str(l.id): l for l in oc.lineas}
        for li in data.lineas:
            oc_linea = oc_lineas_map.get(str(li.oc_linea_id))
            if not oc_linea:
                raise HTTPException(status_code=400, detail=f"Línea de OC no encontrada: {li.oc_linea_id}")
            pendiente = _pendiente_oc_linea(db, oc_linea, excluir_recepcion_id=rec.id)
            if li.cantidad > pendiente:
                raise HTTPException(
                    status_code=400,
                    detail=f"La cantidad {li.cantidad} supera el pendiente ({pendiente}) para '{oc_linea.producto.nombre}'"
                )
            db.add(ComRecepcionLinea(
                recepcion_id=rec.id,
                oc_linea_id=li.oc_linea_id,
                producto_id=oc_linea.producto_id,
                cantidad=li.cantidad,
                um_id=oc_linea.um_id,
                cantidad_base=li.cantidad * (oc_linea.cantidad_base / oc_linea.cantidad) if oc_linea.cantidad else li.cantidad,
                costo_unitario=li.costo_unitario,
            ))

    rec.modificado_por = actor_id
    rec.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return _to_recepcion_response(rec)


def confirmar_recepcion(db: Session, rec_id: uuid.UUID, actor: UsuarioActual) -> RecepcionResponse:
    """
    Confirma la recepción:
    - Para cada línea con maneja_inventario=True: mueve stock + genera asiento
    - Actualiza cantidades recibidas en com_oc_linea
    - Actualiza estado de la OC (en_proceso o recibida_total)
    """
    rec = db.query(ComRecepcion).filter(ComRecepcion.id == rec_id, ComRecepcion.activo == True).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    if rec.estado != "borrador":
        raise HTTPException(status_code=400, detail=f"La recepción ya está en estado '{rec.estado}'")
    if not rec.lineas:
        raise HTTPException(status_code=400, detail="La recepción no tiene líneas")

    actor_id = uuid.UUID(actor.id)
    ahora = datetime.now(timezone.utc)

    # Lock sobre la OC para serializar confirmaciones concurrentes
    oc_locked = db.query(ComOrdenCompra).filter(ComOrdenCompra.id == rec.oc_id).with_for_update().first()
    oc_lineas_map = {str(l.id): l for l in oc_locked.lineas}
    for linea in rec.lineas:
        oc_linea = oc_lineas_map.get(str(linea.oc_linea_id))
        if oc_linea:
            pendiente_confirmado = oc_linea.cantidad - oc_linea.cantidad_recibida
            if linea.cantidad > pendiente_confirmado:
                raise HTTPException(
                    status_code=400,
                    detail=f"Conflicto de concurrencia: la cantidad {linea.cantidad} supera el pendiente real ({pendiente_confirmado}) para '{oc_linea.producto.nombre}'"
                )

    lineas_inventario = [l for l in rec.lineas if l.producto.maneja_inventario]

    # ── Movimiento de inventario (solo líneas con inventario) ─────────────────
    movimiento_id = None
    asiento_id = None
    if lineas_inventario:
        mov = InvMovimiento(
            tipo="ENTRADA_COMPRA",
            fecha=datetime.combine(rec.fecha, datetime.min.time()),
            periodo_id=rec.periodo_id,
            bodega_id=rec.bodega_id,
            numero=rec.numero,
            descripcion=f"Recepción {rec.numero} — OC {rec.oc.numero}",
            estado="confirmado",
            origen_tipo="com_recepcion",
            origen_id=rec.id,
            creado_por=actor_id,
        )
        db.add(mov)
        db.flush()
        movimiento_id = mov.id

        # Estructura por línea: (cuenta_inv, costo, centro_costo_id)
        lineas_asiento: list[tuple] = []
        costo_total_asiento = Decimal("0")

        for linea in lineas_inventario:
            producto = linea.producto
            costo_total_linea = linea.cantidad_base * linea.costo_unitario
            costo_total_asiento += costo_total_linea

            # Línea de movimiento
            db.add(InvMovimientoLinea(
                movimiento_id=mov.id,
                producto_id=linea.producto_id,
                cantidad=linea.cantidad,
                um_id=linea.um_id,
                cantidad_base=linea.cantidad_base,
                costo_unitario=linea.costo_unitario,
                costo_total=costo_total_linea,
            ))

            # Stock — promedio ponderado
            pb = db.query(InvProductoBodega).filter(
                InvProductoBodega.producto_id == linea.producto_id,
                InvProductoBodega.bodega_id == rec.bodega_id,
            ).with_for_update().first()

            if not pb:
                pb = InvProductoBodega(
                    producto_id=linea.producto_id,
                    bodega_id=rec.bodega_id,
                    cantidad=Decimal("0"),
                    costo_promedio=Decimal("0"),
                )
                db.add(pb)
                db.flush()

            stock_actual = pb.cantidad
            costo_actual = pb.costo_promedio
            nueva_cantidad = stock_actual + linea.cantidad_base
            pb.cantidad = nueva_cantidad
            pb.costo_promedio = (
                (stock_actual * costo_actual + costo_total_linea) / nueva_cantidad
                if nueva_cantidad > 0 else linea.costo_unitario
            )

            oc_linea = linea.oc_linea
            cuenta_inv = _resolver_cuenta_inventario(db, producto)
            lineas_asiento.append((cuenta_inv, costo_total_linea, oc_linea))

        # ── Asiento contable ──────────────────────────────────────────────────
        if lineas_asiento and costo_total_asiento > 0:
            cuenta_mercancias = _cuenta_mercancias_recibidas(db)
            if not cuenta_mercancias:
                raise HTTPException(
                    status_code=400,
                    detail="Configure la cuenta 'Mercancías recibidas sin factura' en Parámetros CxP antes de confirmar recepciones"
                )

            moneda_func = db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.activo == True).first()
            if not moneda_func:
                raise HTTPException(status_code=400, detail="No hay moneda funcional configurada")

            td_recp = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "RECP").first()

            asiento = CntAsiento(
                tipo_documento_id=td_recp.id if td_recp else None,
                documento_numero=rec.numero,
                fecha=rec.fecha,
                periodo_id=rec.periodo_id,
                descripcion=f"Recepción {rec.numero} — OC {rec.oc.numero}",
                estado="borrador",
                moneda_id=moneda_func.id,
                documento_origen_id=rec.id,
                documento_origen_tipo="com_recepcion",
                creado_por=actor_id,
            )
            db.add(asiento)
            db.flush()
            asiento_id = asiento.id
            mov.asiento_id = asiento_id

            orden = 1
            for cuenta_inv, costo, oc_linea in lineas_asiento:
                if not cuenta_inv:
                    continue
                # D Inventario
                db.add(CntAsientoLinea(
                    asiento_id=asiento.id,
                    orden=orden,
                    cuenta_id=cuenta_inv.id,
                    descripcion=f"Inventario recepción {rec.numero}",
                    debito=costo,
                    credito=Decimal("0"),
                    debito_funcional=costo,
                    credito_funcional=Decimal("0"),
                    tercero_id=rec.proveedor_id,
                    centro_costo_id=oc_linea.centro_costo_id if oc_linea else None,
                ))
                orden += 1

            total_mercancias = costo_total_asiento
            db.add(CntAsientoLinea(
                asiento_id=asiento.id,
                orden=orden,
                cuenta_id=cuenta_mercancias.id,
                descripcion=f"Mercancías recibidas sin factura {rec.numero}",
                debito=Decimal("0"),
                credito=total_mercancias,
                debito_funcional=Decimal("0"),
                credito_funcional=costo_total_asiento,
                tercero_id=rec.proveedor_id,
            ))

            asiento.estado = "publicado"

    # ── Actualizar cantidades recibidas en OC ──────────────────────────────────
    oc_lineas_map = {str(l.id): l for l in rec.oc.lineas}
    for linea in rec.lineas:
        oc_linea = oc_lineas_map.get(str(linea.oc_linea_id))
        if oc_linea:
            oc_linea.cantidad_recibida += linea.cantidad

    # ── Estado de la OC ───────────────────────────────────────────────────────
    oc = rec.oc
    todas_recibidas = all(
        l.cantidad_recibida >= l.cantidad
        for l in oc.lineas
        if l.producto.maneja_inventario
    )
    oc.estado = "recibida_total" if todas_recibidas else "en_proceso"

    # ── Confirmar recepción ───────────────────────────────────────────────────
    rec.estado = "confirmada"
    rec.movimiento_id = movimiento_id
    rec.asiento_id = asiento_id
    rec.modificado_por = actor_id
    rec.modificado_en = ahora

    db.commit()
    db.refresh(rec)
    return _to_recepcion_response(rec)


def anular_recepcion(db: Session, rec_id: uuid.UUID, actor: UsuarioActual) -> RecepcionResponse:
    rec = db.query(ComRecepcion).filter(ComRecepcion.id == rec_id, ComRecepcion.activo == True).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    if rec.estado == "confirmada":
        raise HTTPException(status_code=400, detail="Una recepción confirmada no puede anularse directamente")
    if rec.estado == "anulada":
        raise HTTPException(status_code=400, detail="La recepción ya está anulada")

    actor_id = uuid.UUID(actor.id)
    rec.estado = "anulada"
    rec.modificado_por = actor_id
    rec.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return _to_recepcion_response(rec)
