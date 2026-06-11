import uuid
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.admin import AdmCondicionPago, AdmMoneda, AdmTipoDocumento
from app.models.adm import AdmTercero
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntCentroCosto, CntCuenta, CntPeriodo
from app.models.cxc import CxcDocumento, CxcParametroContable
from app.models.facturacion import FacFactura, FacFacturaLinea, FacFacturaRetencion, FacResolucion
from app.models.inventario import InvProducto, InvFamilia, InvTipoProducto, InvUnidadMedida
from app.schemas.auth import UsuarioActual
from app.schemas.facturacion import (
    FacFacturaCreate, FacFacturaUpdate, AnularFacturaRequest,
    FacFacturaResponse, FacFacturaListItem, FacListResponse,
    LineaFacResponse, RetencionFacResponse,
)

CODIGO_FAC = "FAC"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _buscar_periodo(db: Session, fecha: date) -> CntPeriodo:
    p = db.query(CntPeriodo).filter(
        CntPeriodo.fecha_inicio <= fecha,
        CntPeriodo.fecha_cierre >= fecha,
        CntPeriodo.activo == True,
    ).first()
    if not p:
        raise HTTPException(status_code=400, detail=f"No existe período contable para la fecha {fecha}")
    return p


def _moneda_funcional(db: Session) -> AdmMoneda:
    m = db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.activo == True).first()
    if not m:
        raise HTTPException(status_code=400, detail="No hay moneda funcional configurada")
    return m


def _generar_numero(db: Session, fecha: date) -> str:
    res = (
        db.query(FacResolucion)
        .filter(
            FacResolucion.tipo == "FACTURA_VENTA",
            FacResolucion.activo == True,
            FacResolucion.fecha_desde <= fecha,
            FacResolucion.fecha_hasta >= fecha,
        )
        .with_for_update()
        .first()
    )
    if not res:
        raise HTTPException(
            status_code=400,
            detail=f"No hay resolución DIAN de facturación vigente para la fecha {fecha}. "
                   "Configura una en Facturación → Resoluciones."
        )
    siguiente = res.consecutivo_actual + 1
    if siguiente < res.rango_desde:
        siguiente = res.rango_desde
    if siguiente > res.rango_hasta:
        raise HTTPException(
            status_code=400,
            detail=f"La resolución DIAN '{res.numero_resolucion}' agotó su rango "
                   f"({res.rango_desde}–{res.rango_hasta}). Registra una nueva resolución."
        )
    res.consecutivo_actual = siguiente
    return f"{res.prefijo or ''}{siguiente}"


def _resolver_cuenta_ingreso(db: Session, linea: FacFacturaLinea) -> CntCuenta | None:
    """Cascade: cuenta_ingreso_id de la línea → producto → familia → tipo_producto."""
    if linea.cuenta_ingreso_id:
        return db.get(CntCuenta, linea.cuenta_ingreso_id)
    if linea.producto_id:
        producto = db.get(InvProducto, linea.producto_id)
        if producto:
            if producto.cuenta_ingreso_id:
                return db.get(CntCuenta, producto.cuenta_ingreso_id)
            if producto.familia_id:
                familia = db.get(InvFamilia, producto.familia_id)
                if familia and familia.cuenta_ingreso_id:
                    return db.get(CntCuenta, familia.cuenta_ingreso_id)
            tipo = db.get(InvTipoProducto, producto.tipo_id)
            if tipo and tipo.cuenta_ingreso_id:
                return db.get(CntCuenta, tipo.cuenta_ingreso_id)
    return None


def _resolver_cuenta_iva(db: Session, linea: FacFacturaLinea, params: CxcParametroContable | None) -> CntCuenta | None:
    if linea.cuenta_iva_id:
        return db.get(CntCuenta, linea.cuenta_iva_id)
    if params and params.cuenta_iva_id:
        return db.get(CntCuenta, params.cuenta_iva_id)
    return None


def _poblar_lineas_asiento(
    db: Session, asiento_id: uuid.UUID, fac: FacFactura,
    cuenta_clientes: CntCuenta, params: CxcParametroContable | None,
    moneda_func: AdmMoneda,
) -> None:
    trm = fac.trm or Decimal("1")
    orden = 1

    def add(cuenta_id, debito, credito, tercero_id=None, centro_costo_id=None):
        nonlocal orden
        d_f = (debito * trm).quantize(Decimal("0.0001")) if fac.moneda_id != moneda_func.id else debito
        c_f = (credito * trm).quantize(Decimal("0.0001")) if fac.moneda_id != moneda_func.id else credito
        db.add(CntAsientoLinea(
            id=uuid.uuid4(), asiento_id=asiento_id, orden=orden,
            cuenta_id=cuenta_id,
            debito=debito, credito=credito,
            debito_funcional=d_f, credito_funcional=c_f,
            tercero_id=tercero_id or fac.cliente_id,
            centro_costo_id=centro_costo_id,
        ))
        orden += 1

    # D Clientes = total neto (subtotal + IVA - retenciones)
    add(cuenta_clientes.id, fac.total, Decimal("0"))

    # D Retenciones a favor (activo) por cada retención
    for ret in fac.retenciones:
        add(ret.cuenta_id, ret.valor, Decimal("0"))

    # C Ingresos + C IVA por línea
    for linea in sorted(fac.lineas, key=lambda l: l.orden):
        cuenta_ingreso = _resolver_cuenta_ingreso(db, linea)
        if not cuenta_ingreso:
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo resolver la cuenta de ingresos para la línea '{linea.descripcion}'. "
                       "Configura la cuenta en el producto, familia o tipo de producto, "
                       "o especifica la cuenta directamente en la línea."
            )
        if cuenta_ingreso.requiere_cc and not linea.centro_costo_id:
            raise HTTPException(
                status_code=400,
                detail=f"La cuenta '{cuenta_ingreso.codigo}' requiere centro de costo. "
                       f"Asígnalo en la línea '{linea.descripcion}'."
            )
        add(cuenta_ingreso.id, Decimal("0"), linea.subtotal, centro_costo_id=linea.centro_costo_id)

        if linea.total_iva > 0:
            cuenta_iva = _resolver_cuenta_iva(db, linea, params)
            if not cuenta_iva:
                raise HTTPException(
                    status_code=400,
                    detail=f"La línea '{linea.descripcion}' tiene IVA pero no tiene cuenta IVA configurada. "
                           "Asígnala en la línea o en Parámetros CxC."
                )
            add(cuenta_iva.id, Decimal("0"), linea.total_iva)


def _to_linea_response(db: Session, linea: FacFacturaLinea) -> LineaFacResponse:
    producto_codigo = producto_nombre = None
    if linea.producto_id:
        p = db.get(InvProducto, linea.producto_id)
        if p:
            producto_codigo, producto_nombre = p.codigo, p.nombre

    um_codigo = None
    if linea.um_id:
        um = db.get(InvUnidadMedida, linea.um_id)
        um_codigo = um.codigo if um else None

    cuenta_iva_codigo = None
    if linea.cuenta_iva_id:
        c = db.get(CntCuenta, linea.cuenta_iva_id)
        cuenta_iva_codigo = c.codigo if c else None

    cuenta_ingreso_codigo = cuenta_ingreso_nombre = None
    if linea.cuenta_ingreso_id:
        c = db.get(CntCuenta, linea.cuenta_ingreso_id)
        if c:
            cuenta_ingreso_codigo, cuenta_ingreso_nombre = c.codigo, c.nombre

    cc_codigo = cc_nombre = None
    if linea.centro_costo_id:
        cc = db.get(CntCentroCosto, linea.centro_costo_id)
        if cc:
            cc_codigo, cc_nombre = cc.codigo, cc.nombre

    return LineaFacResponse(
        id=linea.id, orden=linea.orden,
        producto_id=linea.producto_id,
        producto_codigo=producto_codigo, producto_nombre=producto_nombre,
        descripcion=linea.descripcion,
        cantidad=linea.cantidad,
        um_id=linea.um_id, um_codigo=um_codigo,
        precio_unitario=linea.precio_unitario,
        descuento_pct=linea.descuento_pct, descuento_valor=linea.descuento_valor,
        subtotal=linea.subtotal,
        iva_tipo=linea.iva_tipo, iva_pct=linea.iva_pct, total_iva=linea.total_iva,
        cuenta_iva_id=linea.cuenta_iva_id, cuenta_iva_codigo=cuenta_iva_codigo,
        total=linea.total,
        cuenta_ingreso_id=linea.cuenta_ingreso_id,
        cuenta_ingreso_codigo=cuenta_ingreso_codigo,
        cuenta_ingreso_nombre=cuenta_ingreso_nombre,
        centro_costo_id=linea.centro_costo_id,
        centro_costo_codigo=cc_codigo,
        centro_costo_nombre=cc_nombre,
    )


def _to_retencion_response(db: Session, ret: FacFacturaRetencion) -> RetencionFacResponse:
    cuenta = db.get(CntCuenta, ret.cuenta_id)
    return RetencionFacResponse(
        id=ret.id, tipo=ret.tipo, concepto=ret.concepto,
        base=ret.base, porcentaje=ret.porcentaje, valor=ret.valor,
        cuenta_id=ret.cuenta_id,
        cuenta_codigo=cuenta.codigo if cuenta else None,
        cuenta_nombre=cuenta.nombre if cuenta else None,
    )


def _to_response(fac: FacFactura, db: Session) -> FacFacturaResponse:
    cliente = db.get(AdmTercero, fac.cliente_id)
    moneda = db.get(AdmMoneda, fac.moneda_id)
    condicion_nombre = None
    if fac.condicion_pago_id:
        cp = db.get(AdmCondicionPago, fac.condicion_pago_id)
        condicion_nombre = cp.nombre if cp else None
    return FacFacturaResponse(
        id=fac.id, numero=fac.numero,
        fecha=fac.fecha, fecha_vencimiento=fac.fecha_vencimiento,
        periodo_id=fac.periodo_id,
        cliente_id=fac.cliente_id,
        cliente_nit=cliente.nit if cliente else None,
        cliente_nombre=cliente.razon_social if cliente else None,
        cliente_direccion=cliente.direccion if cliente else None,
        cliente_ciudad=cliente.ciudad if cliente else None,
        cliente_departamento=cliente.departamento if cliente else None,
        cliente_telefono=cliente.telefono if cliente else None,
        cliente_email=cliente.email if cliente else None,
        cliente_regimen=cliente.regimen if cliente else None,
        cliente_responsable_iva=cliente.responsable_iva if cliente else False,
        moneda_id=fac.moneda_id,
        moneda_codigo=moneda.codigo if moneda else "",
        trm=fac.trm,
        condicion_pago_id=fac.condicion_pago_id,
        condicion_pago_nombre=condicion_nombre,
        subtotal=fac.subtotal, total_descuentos=fac.total_descuentos,
        total_iva=fac.total_iva, total_retenciones=fac.total_retenciones,
        total=fac.total,
        notas=fac.notas,
        estado=fac.estado,
        asiento_id=fac.asiento_id,
        asiento_modificado_manual=fac.asiento_modificado_manual,
        cxc_documento_id=fac.cxc_documento_id,
        cufe=fac.cufe,
        fecha_dian=fac.fecha_dian,
        dian_estado=fac.dian_estado,
        lineas=[_to_linea_response(db, l) for l in fac.lineas],
        retenciones=[_to_retencion_response(db, r) for r in fac.retenciones],
        creado_en=fac.creado_en,
        creado_por=fac.creado_por,
    )


def _to_list_item(fac: FacFactura, db: Session, hoy: date) -> FacFacturaListItem:
    cliente = db.get(AdmTercero, fac.cliente_id)
    moneda = db.get(AdmMoneda, fac.moneda_id)
    dias = None
    if fac.fecha_vencimiento and fac.estado == "contabilizada":
        dias = (fac.fecha_vencimiento - hoy).days
    return FacFacturaListItem(
        id=fac.id, numero=fac.numero,
        fecha=fac.fecha, fecha_vencimiento=fac.fecha_vencimiento,
        cliente_nit=cliente.nit if cliente else None,
        cliente_nombre=cliente.razon_social if cliente else None,
        moneda_codigo=moneda.codigo if moneda else "",
        subtotal=fac.subtotal, total_iva=fac.total_iva,
        total_retenciones=fac.total_retenciones, total=fac.total,
        estado=fac.estado,
        dian_estado=fac.dian_estado,
        dias_vencimiento=dias,
    )


def _calcular_totales(lineas_data, retenciones_data):
    subtotal = sum(l.subtotal for l in lineas_data)
    total_iva = sum(l.total_iva for l in lineas_data)
    total_ret = sum(r.valor for r in retenciones_data)
    total_desc = sum(
        (l.precio_unitario * l.cantidad * l.descuento_pct / 100 + l.descuento_valor)
        for l in lineas_data
    )
    total = subtotal + total_iva - total_ret
    return subtotal, total_iva, total_ret, total_desc.quantize(Decimal("0.0001")), total


def _normalizar_iva_tipo(tipo: str, pct: Decimal) -> str:
    if tipo == "GRAVADO":
        return f"GRAVADO_{int(pct)}"
    return tipo


def _persistir_lineas(db: Session, fac_id: uuid.UUID, lineas_data) -> None:
    for i, ld in enumerate(lineas_data, start=1):
        db.add(FacFacturaLinea(
            id=uuid.uuid4(), factura_id=fac_id, orden=i,
            producto_id=ld.producto_id,
            descripcion=ld.descripcion,
            cantidad=ld.cantidad, um_id=ld.um_id,
            precio_unitario=ld.precio_unitario,
            descuento_pct=ld.descuento_pct, descuento_valor=ld.descuento_valor,
            subtotal=ld.subtotal,
            iva_tipo=_normalizar_iva_tipo(ld.iva_tipo, ld.iva_pct),
            iva_pct=ld.iva_pct, total_iva=ld.total_iva,
            cuenta_iva_id=ld.cuenta_iva_id,
            total=ld.total,
            cuenta_ingreso_id=ld.cuenta_ingreso_id,
            centro_costo_id=ld.centro_costo_id,
        ))


def _persistir_retenciones(db: Session, fac_id: uuid.UUID, retenciones_data) -> None:
    for rd in retenciones_data:
        db.add(FacFacturaRetencion(
            id=uuid.uuid4(), factura_id=fac_id,
            tipo=rd.tipo, concepto=rd.concepto,
            base=rd.base, porcentaje=rd.porcentaje, valor=rd.valor,
            cuenta_id=rd.cuenta_id,
        ))


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def listar(
    db: Session,
    pagina: int = 1,
    por_pagina: int = 50,
    estado: str | None = None,
    dian_estado: str | None = None,
    cliente_id: uuid.UUID | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> FacListResponse:
    q = db.query(FacFactura).filter(FacFactura.activo == True)
    if estado:       q = q.filter(FacFactura.estado == estado)
    if dian_estado:  q = q.filter(FacFactura.dian_estado == dian_estado)
    if cliente_id:   q = q.filter(FacFactura.cliente_id == cliente_id)
    if fecha_desde:  q = q.filter(FacFactura.fecha >= fecha_desde)
    if fecha_hasta:  q = q.filter(FacFactura.fecha <= fecha_hasta)
    total = q.count()
    hoy = date.today()
    rows = q.order_by(FacFactura.fecha.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    return FacListResponse(
        items=[_to_list_item(r, db, hoy) for r in rows],
        total=total, pagina=pagina, por_pagina=por_pagina,
    )


def obtener(db: Session, id: uuid.UUID) -> FacFacturaResponse:
    fac = db.query(FacFactura).filter(FacFactura.id == id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return _to_response(fac, db)


def crear(db: Session, data: FacFacturaCreate, actor: UsuarioActual) -> FacFacturaResponse:
    if not data.lineas:
        raise HTTPException(status_code=400, detail="La factura debe tener al menos una línea")

    moneda_func = _moneda_funcional(db)
    if data.moneda_id != moneda_func.id and not data.trm:
        raise HTTPException(status_code=400, detail="Se requiere TRM para moneda extranjera")

    periodo = _buscar_periodo(db, data.fecha)
    numero = _generar_numero(db, data.fecha)

    subtotal, total_iva, total_ret, total_desc, total = _calcular_totales(data.lineas, data.retenciones)

    fac = FacFactura(
        id=uuid.uuid4(), numero=numero,
        fecha=data.fecha, fecha_vencimiento=data.fecha_vencimiento,
        periodo_id=periodo.id,
        cliente_id=data.cliente_id,
        moneda_id=data.moneda_id,
        trm=data.trm if data.moneda_id != moneda_func.id else None,
        condicion_pago_id=data.condicion_pago_id,
        subtotal=subtotal, total_descuentos=total_desc,
        total_iva=total_iva, total_retenciones=total_ret, total=total,
        notas=data.notas,
        estado="borrador",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(fac)
    db.flush()

    _persistir_lineas(db, fac.id, data.lineas)
    _persistir_retenciones(db, fac.id, data.retenciones)

    db.commit()
    db.refresh(fac)
    return _to_response(fac, db)


def actualizar(db: Session, id: uuid.UUID, data: FacFacturaUpdate, actor: UsuarioActual) -> FacFacturaResponse:
    fac = db.query(FacFactura).filter(FacFactura.id == id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if fac.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se pueden editar facturas en borrador")

    moneda_func = _moneda_funcional(db)

    if data.fecha is not None:
        periodo = _buscar_periodo(db, data.fecha)
        fac.periodo_id = periodo.id
        fac.fecha = data.fecha
    if data.fecha_vencimiento is not None:
        fac.fecha_vencimiento = data.fecha_vencimiento
    if data.cliente_id is not None:
        fac.cliente_id = data.cliente_id
    if data.moneda_id is not None:
        fac.moneda_id = data.moneda_id
    if data.trm is not None:
        fac.trm = data.trm if fac.moneda_id != moneda_func.id else None
    if data.condicion_pago_id is not None:
        fac.condicion_pago_id = data.condicion_pago_id
    if data.notas is not None:
        fac.notas = data.notas

    if data.lineas is not None:
        if not data.lineas:
            raise HTTPException(status_code=400, detail="La factura debe tener al menos una línea")
        db.query(FacFacturaLinea).filter(FacFacturaLinea.factura_id == fac.id).delete()
        db.query(FacFacturaRetencion).filter(FacFacturaRetencion.factura_id == fac.id).delete()
        db.flush()
        retenciones = data.retenciones if data.retenciones is not None else []
        subtotal, total_iva, total_ret, total_desc, total = _calcular_totales(data.lineas, retenciones)
        fac.subtotal = subtotal
        fac.total_descuentos = total_desc
        fac.total_iva = total_iva
        fac.total_retenciones = total_ret
        fac.total = total
        _persistir_lineas(db, fac.id, data.lineas)
        _persistir_retenciones(db, fac.id, retenciones)
    elif data.retenciones is not None:
        db.query(FacFacturaRetencion).filter(FacFacturaRetencion.factura_id == fac.id).delete()
        db.flush()
        subtotal, total_iva, total_ret, total_desc, total = _calcular_totales(fac.lineas, data.retenciones)
        fac.total_retenciones = total_ret
        fac.total = total
        _persistir_retenciones(db, fac.id, data.retenciones)

    fac.modificado_por = uuid.UUID(actor.id)
    fac.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fac)
    return _to_response(fac, db)


def contabilizar(db: Session, id: uuid.UUID, actor: UsuarioActual) -> FacFacturaResponse:
    fac = db.query(FacFactura).filter(FacFactura.id == id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if fac.estado != "borrador":
        raise HTTPException(status_code=409, detail="La factura ya está contabilizada o anulada")

    periodo = db.get(CntPeriodo, fac.periodo_id)
    if not periodo or periodo.estado != "abierto":
        raise HTTPException(status_code=400, detail="El período contable no está abierto")

    if fac.total <= 0:
        raise HTTPException(status_code=400, detail="El total de la factura debe ser mayor que cero")

    if not fac.lineas:
        raise HTTPException(status_code=400, detail="La factura no tiene líneas")

    params = db.query(CxcParametroContable).first()
    cuenta_clientes = db.get(CntCuenta, params.cuenta_clientes_id) if params and params.cuenta_clientes_id else None
    if not cuenta_clientes:
        raise HTTPException(
            status_code=400,
            detail="Configura la cuenta de clientes en Administración → Parámetros CxC."
        )

    moneda_func = _moneda_funcional(db)
    td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == CODIGO_FAC).first()

    # Crear asiento
    asiento = CntAsiento(
        id=uuid.uuid4(),
        tipo_documento_id=td.id if td else None,
        documento_numero=fac.numero,
        fecha=fac.fecha,
        periodo_id=fac.periodo_id,
        descripcion=f"FACTURA {fac.numero} — {_get_cliente_nombre(db, fac.cliente_id)}",
        estado="borrador",
        moneda_id=fac.moneda_id,
        trm=fac.trm if fac.moneda_id != moneda_func.id else None,
        documento_origen_id=fac.id,
        documento_origen_tipo="fac_factura",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(asiento)
    db.flush()

    _poblar_lineas_asiento(db, asiento.id, fac, cuenta_clientes, params, moneda_func)
    db.flush()

    # Validar cuadre
    lineas_asiento = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento.id).all()
    total_d = sum(l.debito_funcional for l in lineas_asiento)
    total_c = sum(l.credito_funcional for l in lineas_asiento)
    if abs(total_d - total_c) > Decimal("0.01"):
        raise HTTPException(status_code=400, detail=f"El asiento no cuadra: D={total_d} C={total_c}")

    asiento.estado = "publicado"

    # Crear cxc_documento
    td_fac = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == CODIGO_FAC).first()
    cxc_doc = CxcDocumento(
        id=uuid.uuid4(),
        numero=fac.numero,
        tipo="FACTURA",
        fecha=fac.fecha,
        fecha_vencimiento=fac.fecha_vencimiento,
        periodo_id=fac.periodo_id,
        tercero_id=fac.cliente_id,
        moneda_id=fac.moneda_id,
        trm=fac.trm,
        subtotal=fac.subtotal,
        total_iva=fac.total_iva,
        total_retenciones=fac.total_retenciones,
        total=fac.total,
        saldo=fac.total,
        descripcion=fac.notas,
        estado="contabilizado",
        asiento_id=asiento.id,
        condicion_pago_id=fac.condicion_pago_id,
        origen_modulo="fac_factura",
        origen_id=fac.id,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(cxc_doc)
    db.flush()

    fac.asiento_id = asiento.id
    fac.cxc_documento_id = cxc_doc.id
    fac.estado = "contabilizada"
    fac.dian_estado = "pendiente"
    fac.modificado_por = uuid.UUID(actor.id)
    fac.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(fac)
    return _to_response(fac, db)


def anular(db: Session, id: uuid.UUID, data: AnularFacturaRequest, actor: UsuarioActual) -> FacFacturaResponse:
    fac = db.query(FacFactura).filter(FacFactura.id == id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if fac.estado == "anulada":
        raise HTTPException(status_code=409, detail="La factura ya está anulada")
    if fac.estado == "borrador":
        # Borrador: soft delete directo, sin contraasiento
        fac.activo = False
        fac.estado = "anulada"
        fac.modificado_por = uuid.UUID(actor.id)
        fac.modificado_en = datetime.now(timezone.utc)
        db.commit()
        db.refresh(fac)
        return _to_response(fac, db)

    # Contabilizada: verificar que no tenga pagos aplicados
    if fac.cxc_documento_id:
        from app.models.cxc import CxcAplicacion
        aplicado = db.query(CxcAplicacion).filter(
            CxcAplicacion.documento_debito_id == fac.cxc_documento_id,
            CxcAplicacion.estado == "aplicado",
        ).first()
        if aplicado:
            raise HTTPException(
                status_code=409,
                detail="No se puede anular — la factura tiene recibos de caja aplicados."
            )

    periodo = db.get(CntPeriodo, fac.periodo_id)
    if not periodo or periodo.estado != "abierto":
        raise HTTPException(status_code=400, detail="El período contable no está abierto. No se puede anular.")

    moneda_func = _moneda_funcional(db)
    asiento_orig = db.get(CntAsiento, fac.asiento_id) if fac.asiento_id else None

    if asiento_orig:
        lineas_orig = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento_orig.id).all()
        td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "ANU").first()
        contra = CntAsiento(
            id=uuid.uuid4(),
            tipo_documento_id=td.id if td else None,
            documento_numero=f"ANU-{fac.numero}",
            fecha=date.today(),
            periodo_id=fac.periodo_id,
            descripcion=f"ANULACIÓN FACTURA {fac.numero} — {data.motivo}",
            estado="publicado",
            moneda_id=fac.moneda_id,
            trm=fac.trm if fac.moneda_id != moneda_func.id else None,
            documento_origen_id=fac.id,
            documento_origen_tipo="fac_factura_anulacion",
            creado_por=uuid.UUID(actor.id),
        )
        db.add(contra)
        db.flush()
        for i, l in enumerate(lineas_orig, start=1):
            d_f = l.credito_funcional
            c_f = l.debito_funcional
            db.add(CntAsientoLinea(
                id=uuid.uuid4(), asiento_id=contra.id, orden=i,
                cuenta_id=l.cuenta_id,
                debito=l.credito, credito=l.debito,
                debito_funcional=d_f, credito_funcional=c_f,
                tercero_id=l.tercero_id,
            ))

    # Anular cxc_documento: saldo → 0
    if fac.cxc_documento_id:
        cxc_doc = db.get(CxcDocumento, fac.cxc_documento_id)
        if cxc_doc:
            cxc_doc.estado = "anulado"
            cxc_doc.saldo = Decimal("0")

    fac.estado = "anulada"
    fac.activo = False
    fac.modificado_por = uuid.UUID(actor.id)
    fac.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(fac)
    return _to_response(fac, db)


def _get_cliente_nombre(db: Session, cliente_id: uuid.UUID) -> str:
    t = db.get(AdmTercero, cliente_id)
    return t.razon_social if t else ""
