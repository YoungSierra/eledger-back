import uuid
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.admin import AdmCondicionPago, AdmMoneda, AdmTarifaIva, AdmTipoDocumento
from app.models.adm import AdmTercero
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntCentroCosto, CntCuenta, CntPeriodo
from app.models.cxc import CxcDocumento, CxcParametroContable
from app.models.cxp import CxpDocumento, CxpDocumentoLinea
from app.models.facturacion import FacFactura, FacFacturaLinea, FacFacturaRetencion, FacResolucion
from app.models.inventario import InvProducto, InvFamilia, InvTipoProducto, InvUnidadMedida
from app.models.ope import OpeCotizacion, OpeCotizacionLinea, OpeConcepto
from app.schemas.auth import UsuarioActual
from app.schemas.facturacion import (
    FacFacturaCreate, FacFacturaUpdate, AnularFacturaRequest,
    FacFacturaResponse, FacFacturaListItem, FacListResponse,
    LineaFacResponse, RetencionFacResponse,
    LineaFacCreate, FacturarCotizacionRequest,
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


def _resolver_cuenta_vrt(db: Session, linea: FacFacturaLinea, params: CxcParametroContable | None) -> CntCuenta | None:
    """Valor recibido para tercero: cuenta del concepto (cuenta_ingreso_id de la línea,
    donde el usuario configura la 2815) → fallback al parámetro global de Parámetros CxC."""
    if linea.cuenta_ingreso_id:
        return db.get(CntCuenta, linea.cuenta_ingreso_id)
    if params and params.cuenta_valores_terceros_id:
        return db.get(CntCuenta, params.cuenta_valores_terceros_id)
    return None


def construir_asiento(
    db: Session, fac: FacFactura,
    cuenta_clientes: CntCuenta | None, params: CxcParametroContable | None,
    preview: bool = False,
) -> tuple[list[dict], list[str]]:
    """Arma las líneas del asiento de la factura (sin persistir).
    Retorna (lineas, avisos). En preview=True acumula avisos en vez de lanzar."""
    avisos: list[str] = []
    lineas: list[dict] = []

    def problema(msg: str):
        if preview:
            avisos.append(msg)
        else:
            raise HTTPException(status_code=400, detail=msg)

    def add(cuenta: CntCuenta | None, debito, credito, tercero_id=None, tercero_nombre=None, centro_costo_id=None):
        cc_txt = None
        if centro_costo_id:
            cc = db.get(CntCentroCosto, centro_costo_id)
            cc_txt = f"{cc.codigo} {cc.nombre}" if cc else None
        lineas.append({
            "cuenta_id": cuenta.id if cuenta else None,
            "cuenta_codigo": cuenta.codigo if cuenta else None,
            "cuenta_nombre": cuenta.nombre if cuenta else "(sin cuenta)",
            "tercero_id": tercero_id or fac.cliente_id,
            "tercero_nombre": tercero_nombre or _get_cliente_nombre(db, fac.cliente_id),
            "centro_costo_id": centro_costo_id,
            "centro_costo": cc_txt,
            "debito": debito, "credito": credito,
        })

    if not cuenta_clientes:
        problema("Configura la cuenta de clientes en Administración → Parámetros CxC.")

    # D Clientes = total neto (subtotal + IVA - retenciones)
    add(cuenta_clientes, fac.total, Decimal("0"))

    # D Retenciones a favor (activo)
    for ret in fac.retenciones:
        cta_ret = db.get(CntCuenta, ret.cuenta_id) if ret.cuenta_id else None
        if not cta_ret:
            problema(f"La retención '{ret.concepto}' no tiene cuenta contable.")
        add(cta_ret, ret.valor, Decimal("0"))

    # C por línea: propio → ingreso (+IVA); tercero → cuenta 2815 con submayor proveedor
    for linea in sorted(fac.lineas, key=lambda l: l.orden):
        if linea.valor_tercero:
            cta_vrt = _resolver_cuenta_vrt(db, linea, params)
            if not cta_vrt:
                problema(f"La línea '{linea.descripcion}' es valor para tercero pero no tiene cuenta: "
                         "configúrala en el concepto o en Parámetros CxC (cuenta valores para terceros).")
            prov_nombre = _get_cliente_nombre(db, linea.proveedor_id) if linea.proveedor_id else None
            add(cta_vrt, Decimal("0"), linea.subtotal,
                tercero_id=linea.proveedor_id, tercero_nombre=prov_nombre,
                centro_costo_id=linea.centro_costo_id)
            continue

        cuenta_ingreso = _resolver_cuenta_ingreso(db, linea)
        if not cuenta_ingreso:
            if linea.cotizacion_linea_id:
                problema(f"No se pudo resolver la cuenta de ingresos para el concepto '{linea.descripcion}'. "
                         "Configura la cuenta de ingreso en el concepto (Operaciones → Conceptos).")
            else:
                problema(f"No se pudo resolver la cuenta de ingresos para la línea '{linea.descripcion}'. "
                         "Configura la cuenta en el producto, familia o tipo de producto, "
                         "o especifica la cuenta directamente en la línea.")
        elif cuenta_ingreso.requiere_cc and not linea.centro_costo_id:
            problema(f"La cuenta '{cuenta_ingreso.codigo}' requiere centro de costo. "
                     f"Asígnalo en la línea '{linea.descripcion}'.")
        add(cuenta_ingreso, Decimal("0"), linea.subtotal, centro_costo_id=linea.centro_costo_id)

        if linea.total_iva > 0:
            cuenta_iva = _resolver_cuenta_iva(db, linea, params)
            if not cuenta_iva:
                problema(f"La línea '{linea.descripcion}' tiene IVA pero no tiene cuenta IVA configurada. "
                         "Asígnala en la línea o en Parámetros CxC.")
            add(cuenta_iva, Decimal("0"), linea.total_iva)

    return lineas, avisos


def _poblar_lineas_asiento(
    db: Session, asiento_id: uuid.UUID, fac: FacFactura,
    cuenta_clientes: CntCuenta, params: CxcParametroContable | None,
    moneda_func: AdmMoneda,
) -> None:
    trm = fac.trm or Decimal("1")
    lineas, _ = construir_asiento(db, fac, cuenta_clientes, params, preview=False)
    for orden, l in enumerate(lineas, start=1):
        debito, credito = l["debito"], l["credito"]
        d_f = (debito * trm).quantize(Decimal("0.0001")) if fac.moneda_id != moneda_func.id else debito
        c_f = (credito * trm).quantize(Decimal("0.0001")) if fac.moneda_id != moneda_func.id else credito
        db.add(CntAsientoLinea(
            id=uuid.uuid4(), asiento_id=asiento_id, orden=orden,
            cuenta_id=l["cuenta_id"],
            debito=debito, credito=credito,
            debito_funcional=d_f, credito_funcional=c_f,
            tercero_id=l["tercero_id"],
            centro_costo_id=l["centro_costo_id"],
        ))


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
        cotizacion_linea_id=linea.cotizacion_linea_id,
        monto_cotizacion=linea.monto_cotizacion,
        valor_tercero=linea.valor_tercero,
        proveedor_id=linea.proveedor_id,
        proveedor_nombre=linea.proveedor_nombre,
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
        cotizacion_id=fac.cotizacion_id,
        cotizacion_numero=(db.get(OpeCotizacion, fac.cotizacion_id).numero if fac.cotizacion_id else None),
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
    # Saldo del CxC asociado: si ya está pagada (saldo 0) no se muestra vencimiento.
    saldo = None
    pagada = False
    if fac.cxc_documento_id:
        cxc = db.get(CxcDocumento, fac.cxc_documento_id)
        if cxc:
            saldo = cxc.saldo
            pagada = cxc.saldo <= 0
    dias = None
    if fac.fecha_vencimiento and fac.estado == "contabilizada" and not pagada:
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
        saldo=saldo,
        pagada=pagada,
        creado_en=fac.creado_en,
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
        es_tercero = getattr(ld, "valor_tercero", False)
        proveedor_id = getattr(ld, "proveedor_id", None)
        if es_tercero and not proveedor_id:
            raise HTTPException(
                status_code=400,
                detail=f"La línea '{ld.descripcion}' es valor para tercero: debe indicar el proveedor al que se traslada.",
            )
        # Un valor para tercero no genera IVA propio: se fuerza a cero.
        iva_tipo = "NINGUNO" if es_tercero else _normalizar_iva_tipo(ld.iva_tipo, ld.iva_pct)
        iva_pct = Decimal("0") if es_tercero else ld.iva_pct
        total_iva = Decimal("0") if es_tercero else ld.total_iva
        db.add(FacFacturaLinea(
            id=uuid.uuid4(), factura_id=fac_id, orden=i,
            producto_id=ld.producto_id,
            descripcion=ld.descripcion,
            cantidad=ld.cantidad, um_id=ld.um_id,
            precio_unitario=ld.precio_unitario,
            descuento_pct=ld.descuento_pct, descuento_valor=ld.descuento_valor,
            subtotal=ld.subtotal,
            iva_tipo=iva_tipo,
            iva_pct=iva_pct, total_iva=total_iva,
            cuenta_iva_id=None if es_tercero else ld.cuenta_iva_id,
            total=ld.total,
            cuenta_ingreso_id=ld.cuenta_ingreso_id,
            centro_costo_id=ld.centro_costo_id,
            cotizacion_linea_id=getattr(ld, "cotizacion_linea_id", None),
            monto_cotizacion=getattr(ld, "monto_cotizacion", None),
            valor_tercero=es_tercero,
            proveedor_id=proveedor_id,
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
    rows = q.order_by(FacFactura.fecha.desc(), FacFactura.creado_en.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    return FacListResponse(
        items=[_to_list_item(r, db, hoy) for r in rows],
        total=total, pagina=pagina, por_pagina=por_pagina,
    )


def obtener(db: Session, id: uuid.UUID) -> FacFacturaResponse:
    fac = db.query(FacFactura).filter(FacFactura.id == id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return _to_response(fac, db)


def _facturado_por_linea(db: Session, cotizacion_id: uuid.UUID, excluir_factura_id: uuid.UUID | None = None) -> dict:
    """Monto ya facturado por línea de cotización (facturas no anuladas), en su moneda nativa."""
    q = (
        db.query(FacFacturaLinea.cotizacion_linea_id, func.coalesce(func.sum(FacFacturaLinea.monto_cotizacion), 0))
        .join(FacFactura, FacFacturaLinea.factura_id == FacFactura.id)
        .filter(FacFactura.cotizacion_id == cotizacion_id, FacFactura.estado != "anulada",
                FacFacturaLinea.cotizacion_linea_id.isnot(None))
    )
    if excluir_factura_id:
        q = q.filter(FacFactura.id != excluir_factura_id)
    return {lid: Decimal(str(m or 0)) for lid, m in q.group_by(FacFacturaLinea.cotizacion_linea_id).all()}


def estado_facturacion_cotizacion(db: Session, cotizacion_id: uuid.UUID, excluir_factura_id: uuid.UUID | None = None) -> dict:
    cot = db.get(OpeCotizacion, cotizacion_id)
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    facturado = _facturado_por_linea(db, cotizacion_id, excluir_factura_id)
    lineas, algo_fact, algo_pend = [], False, False
    TOL = Decimal("0.0001")
    for l in sorted(cot.lineas, key=lambda x: (x.seccion, x.orden)):
        fact = facturado.get(l.id, Decimal("0"))
        pend = Decimal(str(l.total_venta)) - fact
        if fact > TOL:
            algo_fact = True
        if pend > TOL:
            algo_pend = True
        # Parámetros de facturación del concepto (cuenta de ingreso + IVA).
        concepto = db.get(OpeConcepto, l.concepto_id) if l.concepto_id else None
        cta = db.get(CntCuenta, concepto.cuenta_ingreso_id) if concepto and concepto.cuenta_ingreso_id else None
        tarifa = db.get(AdmTarifaIva, concepto.tarifa_iva_id) if concepto and concepto.tarifa_iva_id else None
        cta_iva = db.get(CntCuenta, tarifa.cuenta_iva_ventas_id) if tarifa and tarifa.cuenta_iva_ventas_id else None
        um = db.get(InvUnidadMedida, concepto.um_id) if concepto and concepto.um_id else None
        prov = db.get(AdmTercero, l.proveedor_id) if l.proveedor_id else None
        lineas.append({
            "linea_id": str(l.id), "seccion": l.seccion, "descripcion": l.descripcion,
            "moneda": l.moneda, "total_venta": str(l.total_venta),
            "facturado": str(fact), "pendiente": str(pend if pend > 0 else Decimal("0")),
            "cuenta_ingreso_id": str(cta.id) if cta else None,
            "cuenta_ingreso_display": f"{cta.codigo} {cta.nombre}" if cta else None,
            "tarifa_iva_id": str(tarifa.id) if tarifa else None,
            "iva_pct": str(tarifa.porcentaje) if tarifa else "0",
            "cuenta_iva_id": str(cta_iva.id) if cta_iva else None,
            "cuenta_iva_display": f"{cta_iva.codigo} {cta_iva.nombre}" if cta_iva else None,
            "um_id": str(um.id) if um else None,
            "um_codigo": um.codigo if um else None,
            "valor_tercero": l.valor_tercero,
            "proveedor_id": str(l.proveedor_id) if l.proveedor_id else None,
            "proveedor_display": f"{prov.nit} — {prov.razon_social}" if prov else None,
        })
    estado = "facturada" if (algo_fact and not algo_pend) else ("parcial" if algo_fact else "pendiente")
    return {"cotizacion_id": str(cot.id), "numero": cot.numero, "trm": str(cot.trm or 0),
            "estado_facturacion": estado, "lineas": lineas}


def _validar_lineas_cotizacion(db: Session, data: FacFacturaCreate) -> None:
    if not data.cotizacion_id:
        return
    facturado = _facturado_por_linea(db, data.cotizacion_id)
    TOL = Decimal("0.0001")
    acumulado: dict = {}
    for ld in data.lineas:
        lid = getattr(ld, "cotizacion_linea_id", None)
        if not lid:
            continue
        cl = db.get(OpeCotizacionLinea, lid)
        if not cl or cl.cotizacion_id != data.cotizacion_id:
            raise HTTPException(status_code=400, detail="Una línea referencia una cotización distinta a la de la factura")
        monto = Decimal(str(getattr(ld, "monto_cotizacion", None) or 0))
        acumulado[lid] = acumulado.get(lid, Decimal("0")) + monto
        pendiente = Decimal(str(cl.total_venta)) - facturado.get(lid, Decimal("0"))
        if acumulado[lid] - pendiente > TOL:
            raise HTTPException(status_code=400,
                detail=f"El monto a facturar de '{cl.descripcion}' excede el pendiente ({pendiente}).")


def crear(db: Session, data: FacFacturaCreate, actor: UsuarioActual) -> FacFacturaResponse:
    if not data.lineas:
        raise HTTPException(status_code=400, detail="La factura debe tener al menos una línea")
    _validar_lineas_cotizacion(db, data)

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
        cotizacion_id=data.cotizacion_id,
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


def facturar_cotizacion(db: Session, cotizacion_id: uuid.UUID, req: FacturarCotizacionRequest, actor: UsuarioActual) -> FacFacturaResponse:
    """Genera una factura de venta (borrador) desde las líneas de una cotización.
    El monto de cada línea viene en la moneda nativa de la cotización; se convierte
    a la moneda de la factura con la TRM de la cotización. Cuenta de ingreso e IVA
    salen del concepto de cada línea."""
    cot = db.get(OpeCotizacion, cotizacion_id)
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    moneda = db.query(AdmMoneda).filter(AdmMoneda.codigo == req.moneda, AdmMoneda.activo == True).first()
    if not moneda:
        raise HTTPException(status_code=400, detail=f"Moneda {req.moneda} no encontrada")
    moneda_func = _moneda_funcional(db)
    # En factura prevalece la TRM del DÍA (no la de la cotización).
    from app.models.admin import AdmTrm
    hoy = date.today()
    trm_row = (
        db.query(AdmTrm)
        .filter(AdmTrm.fecha >= datetime(hoy.year, hoy.month, hoy.day),
                AdmTrm.fecha < datetime(hoy.year, hoy.month, hoy.day, 23, 59, 59))
        .first()
    )
    trm = Decimal(str(trm_row.tasa)) if trm_row and trm_row.tasa else Decimal("0")
    if moneda.id != moneda_func.id and trm <= 0:
        raise HTTPException(status_code=400, detail="No hay TRM del día registrada. Regístrala para facturar en moneda extranjera.")

    def conv(valor: Decimal, desde: str) -> Decimal:
        if desde == req.moneda:
            return valor
        return (valor / trm) if req.moneda == "USD" else (valor * trm)

    lineas: list[LineaFacCreate] = []
    for item in req.lineas:
        monto = Decimal(str(item.monto or 0))
        if monto <= 0:
            continue
        cl = db.get(OpeCotizacionLinea, item.cotizacion_linea_id)
        if not cl or cl.cotizacion_id != cot.id:
            raise HTTPException(status_code=400, detail="Una línea no pertenece a esta cotización")
        concepto = db.get(OpeConcepto, cl.concepto_id) if cl.concepto_id else None
        if not concepto or not concepto.cuenta_ingreso_id:
            raise HTTPException(status_code=400,
                detail=f"El concepto de '{cl.descripcion}' no tiene cuenta de ingreso configurada")
        tarifa = db.get(AdmTarifaIva, concepto.tarifa_iva_id) if concepto.tarifa_iva_id else None
        pct = Decimal(str(tarifa.porcentaje)) if tarifa else Decimal("0")

        subtotal = conv(monto, cl.moneda).quantize(Decimal("0.0001"))
        total_iva = (subtotal * pct / Decimal("100")).quantize(Decimal("0.0001"))
        lineas.append(LineaFacCreate(
            descripcion=cl.descripcion,
            cantidad=Decimal("1"),
            um_id=concepto.um_id,
            precio_unitario=subtotal,
            subtotal=subtotal,
            iva_tipo="GRAVADO" if pct > 0 else "NINGUNO",
            iva_pct=pct,
            total_iva=total_iva,
            cuenta_iva_id=tarifa.cuenta_iva_ventas_id if tarifa else None,
            total=subtotal + total_iva,
            cuenta_ingreso_id=concepto.cuenta_ingreso_id,
            cotizacion_linea_id=cl.id,
            monto_cotizacion=monto,
        ))

    if not lineas:
        raise HTTPException(status_code=400, detail="Selecciona al menos una línea con monto a facturar")

    data = FacFacturaCreate(
        fecha=req.fecha, fecha_vencimiento=req.fecha_vencimiento,
        cliente_id=cot.cliente_id, cotizacion_id=cot.id,
        moneda_id=moneda.id, trm=(trm if moneda.id != moneda_func.id else None),
        condicion_pago_id=req.condicion_pago_id, notas=req.notas,
        lineas=lineas, retenciones=[],
    )
    return crear(db, data, actor)


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


def _generar_vrt_documentos(db: Session, fac: FacFactura, params: CxcParametroContable | None, actor: UsuarioActual) -> None:
    """Crea un documento CxP tipo VRT por cada proveedor con líneas de valor tercero.
    NO genera asiento propio: el crédito a 2815 ya lo hizo la factura de venta."""
    from app.services import cxp_service
    tercero_lineas = [l for l in fac.lineas if l.valor_tercero and l.proveedor_id]
    if not tercero_lineas:
        return
    grupos: dict = {}
    for l in tercero_lineas:
        grupos.setdefault(l.proveedor_id, []).append(l)

    for prov_id, lns in grupos.items():
        total = sum((l.subtotal for l in lns), Decimal("0"))
        doc = CxpDocumento(
            id=uuid.uuid4(),
            numero=cxp_service._generar_numero(db, "VRT"),
            tipo="VRT",
            fecha=fac.fecha,
            fecha_vencimiento=fac.fecha_vencimiento,
            periodo_id=fac.periodo_id,
            tercero_id=prov_id,
            moneda_id=fac.moneda_id,
            trm=fac.trm,
            subtotal=total, total_iva=Decimal("0"),
            total_retenciones=Decimal("0"), total=total, saldo=total,
            descripcion=f"Valores recibidos para tercero — factura {fac.numero}",
            estado="contabilizado",
            asiento_id=None,
            origen_modulo="fac_factura",
            origen_id=fac.id,
            creado_por=uuid.UUID(actor.id),
        )
        db.add(doc)
        db.flush()
        for orden, l in enumerate(lns, start=1):
            cta = _resolver_cuenta_vrt(db, l, params)
            db.add(CxpDocumentoLinea(
                id=uuid.uuid4(), documento_id=doc.id, orden=orden,
                descripcion=l.descripcion, concepto_id=None,
                cuenta_id=cta.id if cta else None,
                subtotal=l.subtotal, iva_pct=Decimal("0"), total_iva=Decimal("0"),
                total=l.subtotal, iva_tipo="NINGUNO",
            ))


def preview_asiento(db: Session, data: FacFacturaCreate) -> "PreviewAsientoResponse":
    from app.schemas.facturacion import PreviewAsientoResponse, PreviewAsientoLinea
    moneda_func = _moneda_funcional(db)
    params = db.query(CxcParametroContable).first()
    cuenta_clientes = db.get(CntCuenta, params.cuenta_clientes_id) if params and params.cuenta_clientes_id else None

    subtotal, total_iva, total_ret, _td, total = _calcular_totales(data.lineas, data.retenciones)

    # Factura transitoria (no se persiste) — replica la normalización de _persistir_lineas.
    fac = FacFactura(
        id=uuid.uuid4(), cliente_id=data.cliente_id,
        moneda_id=data.moneda_id, trm=data.trm,
        subtotal=subtotal, total_iva=total_iva, total_retenciones=total_ret, total=total,
    )
    fac.lineas = []
    for i, ld in enumerate(data.lineas, start=1):
        es_ter = getattr(ld, "valor_tercero", False)
        fac.lineas.append(FacFacturaLinea(
            id=uuid.uuid4(), orden=i, producto_id=ld.producto_id,
            descripcion=ld.descripcion, cantidad=ld.cantidad,
            precio_unitario=ld.precio_unitario, subtotal=ld.subtotal,
            iva_tipo="NINGUNO" if es_ter else _normalizar_iva_tipo(ld.iva_tipo, ld.iva_pct),
            iva_pct=Decimal("0") if es_ter else ld.iva_pct,
            total_iva=Decimal("0") if es_ter else ld.total_iva,
            cuenta_iva_id=None if es_ter else ld.cuenta_iva_id,
            total=ld.total, cuenta_ingreso_id=ld.cuenta_ingreso_id,
            centro_costo_id=ld.centro_costo_id,
            cotizacion_linea_id=getattr(ld, "cotizacion_linea_id", None),
            valor_tercero=es_ter, proveedor_id=getattr(ld, "proveedor_id", None),
        ))
    fac.retenciones = [
        FacFacturaRetencion(id=uuid.uuid4(), tipo=r.tipo, concepto=r.concepto,
                            base=r.base, porcentaje=r.porcentaje, valor=r.valor, cuenta_id=r.cuenta_id)
        for r in data.retenciones
    ]

    lineas, avisos = construir_asiento(db, fac, cuenta_clientes, params, preview=True)
    total_d = sum((l["debito"] for l in lineas), Decimal("0"))
    total_c = sum((l["credito"] for l in lineas), Decimal("0"))
    moneda = db.get(AdmMoneda, data.moneda_id)
    return PreviewAsientoResponse(
        lineas=[PreviewAsientoLinea(
            cuenta_codigo=l["cuenta_codigo"], cuenta_nombre=l["cuenta_nombre"],
            tercero_nombre=l["tercero_nombre"], centro_costo=l["centro_costo"],
            debito=l["debito"], credito=l["credito"],
        ) for l in lineas],
        total_debito=total_d, total_credito=total_c,
        cuadra=abs(total_d - total_c) <= Decimal("0.01"),
        moneda_codigo=moneda.codigo if moneda else None,
        avisos=avisos,
    )


def asiento_contabilizado(db: Session, id: uuid.UUID) -> "PreviewAsientoResponse":
    """Líneas del asiento REAL ya contabilizado de la factura de venta."""
    from app.schemas.facturacion import PreviewAsientoResponse, PreviewAsientoLinea
    fac = db.query(FacFactura).filter(FacFactura.id == id).first()
    if not fac or not fac.asiento_id:
        return PreviewAsientoResponse(
            lineas=[], total_debito=Decimal("0"), total_credito=Decimal("0"),
            cuadra=True, moneda_codigo=None,
            avisos=["La factura aún no tiene asiento contabilizado."],
        )
    asiento = db.get(CntAsiento, fac.asiento_id)
    lineas = db.query(CntAsientoLinea).filter(
        CntAsientoLinea.asiento_id == fac.asiento_id
    ).order_by(CntAsientoLinea.orden).all()
    out = []
    for l in lineas:
        c = db.get(CntCuenta, l.cuenta_id) if l.cuenta_id else None
        terc = db.get(AdmTercero, l.tercero_id) if l.tercero_id else None
        cc = db.get(CntCentroCosto, l.centro_costo_id) if l.centro_costo_id else None
        out.append(PreviewAsientoLinea(
            cuenta_codigo=c.codigo if c else None,
            cuenta_nombre=c.nombre if c else None,
            tercero_nombre=terc.razon_social if terc else None,
            centro_costo=f"{cc.codigo} {cc.nombre}" if cc else None,
            debito=l.debito, credito=l.credito,
        ))
    total_d = sum((l.debito for l in lineas), Decimal("0"))
    total_c = sum((l.credito for l in lineas), Decimal("0"))
    moneda = db.get(AdmMoneda, fac.moneda_id)
    return PreviewAsientoResponse(
        lineas=out, total_debito=total_d, total_credito=total_c,
        cuadra=abs(total_d - total_c) <= Decimal("0.01"),
        moneda_codigo=moneda.codigo if moneda else None, avisos=[],
        asiento_numero=asiento.numero if asiento else None,
    )


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

    # Generar documento(s) VRT en CxP por las líneas de valor tercero (sin asiento propio).
    _generar_vrt_documentos(db, fac, params, actor)

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

    # VRT (valores recibidos para terceros) generados por esta factura: bloquear si alguno ya tiene pago
    from app.models.cxp import CxpAplicacion
    vrts = db.query(CxpDocumento).filter(
        CxpDocumento.origen_modulo == "fac_factura",
        CxpDocumento.origen_id == fac.id,
        CxpDocumento.tipo == "VRT",
        CxpDocumento.estado != "anulado",
    ).all()
    for v in vrts:
        pagado = (v.saldo is not None and v.total is not None and v.saldo < v.total)
        ap = db.query(CxpAplicacion).filter(CxpAplicacion.documento_debito_id == v.id).first()
        if pagado or ap:
            raise HTTPException(
                status_code=409,
                detail=f"No se puede anular: el valor para tercero {v.numero} ya tiene un pago. "
                       "Reversa/anula el comprobante de pago antes de anular la factura.",
            )

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

    # Anular los VRT generados (sin contraasiento propio: el crédito a 2815 ya lo
    # reversa el contraasiento de la factura, que revierte todas sus líneas).
    for v in vrts:
        v.estado = "anulado"
        v.saldo = Decimal("0")
        v.modificado_por = uuid.UUID(actor.id)
        v.modificado_en = datetime.now(timezone.utc)

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
