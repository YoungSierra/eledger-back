import uuid
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.admin import AdmConcepto, AdmMoneda, AdmTipoDocumento, AdmConsecutivo
from app.models.adm import AdmTercero
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntCuenta, CntPeriodo
from app.models.bancos import BanCuenta
from app.models.cxp import CxpDocumento, CxpDocumentoLinea, CxpLineaRetencion, CxpParametroContable, CxpAplicacion
from app.schemas.auth import UsuarioActual
from app.schemas.cxp import (
    CxpDocumentoCreate, CxpDocumentoUpdate, AnularCxpRequest,
    CxpDocumentoResponse, CxpDocumentoListItem, CxpListResponse,
    CxpLineaResponse, LineaRetencionResponse,
    CxpResumenItem, CxpResumenResponse,
    ComprobanteCreate, FacturaPendienteCxpItem, AplicacionPendienteCxpItem,
)

TIPO_A_CODIGO = {
    "FACTURA":      "FCP",
    "COMPROBANTE":  "CP",
    "NOTA_CREDITO": "NCC",
    "NOTA_DEBITO":  "NDB",
    "ANTICIPO":     "ANTP",
}


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


def _get_tercero_nombre(db: Session, tercero_id: uuid.UUID) -> str:
    t = db.get(AdmTercero, tercero_id)
    return t.razon_social if t else ""


def _generar_numero(db: Session, tipo: str) -> str:
    codigo = TIPO_A_CODIGO.get(tipo, tipo)
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
    resultado = f"{cons.prefijo or ''}{str(siguiente).zfill(cons.longitud_minima)}"
    cons.numero_actual = siguiente
    return resultado


def _resolver_cuenta_gasto(db: Session, linea: CxpDocumentoLinea) -> CntCuenta | None:
    if linea.cuenta_id:
        return db.get(CntCuenta, linea.cuenta_id)
    if linea.concepto_id:
        concepto = db.get(AdmConcepto, linea.concepto_id)
        if concepto and concepto.cuenta_gasto_id:
            return db.get(CntCuenta, concepto.cuenta_gasto_id)
    return None


def _resolver_cuenta_cxp(db: Session, linea: CxpDocumentoLinea, fallback_id: uuid.UUID | None) -> CntCuenta | None:
    """Cuenta CxP (Proveedores) para acreditar en esta línea."""
    if linea.concepto_id:
        concepto = db.get(AdmConcepto, linea.concepto_id)
        if concepto and concepto.cuenta_cxp_id:
            return db.get(CntCuenta, concepto.cuenta_cxp_id)
    if fallback_id:
        return db.get(CntCuenta, fallback_id)
    return None


def _poblar_lineas_asiento(
    db: Session, asiento_id: uuid.UUID, doc: CxpDocumento,
    fallback_cxp_id: uuid.UUID | None, moneda_func: AdmMoneda,
) -> None:
    trm = doc.trm or Decimal("1")
    orden = 1

    def add_linea(cuenta_id, debito, credito, centro_costo_id=None):
        nonlocal orden
        d_func = (debito * trm).quantize(Decimal("0.0001")) if doc.moneda_id != moneda_func.id else debito
        c_func = (credito * trm).quantize(Decimal("0.0001")) if doc.moneda_id != moneda_func.id else credito
        db.add(CntAsientoLinea(
            id=uuid.uuid4(), asiento_id=asiento_id, orden=orden,
            cuenta_id=cuenta_id,
            debito=debito, credito=credito,
            debito_funcional=d_func, credito_funcional=c_func,
            tercero_id=doc.tercero_id,
            centro_costo_id=centro_costo_id,
        ))
        orden += 1

    for linea in sorted(doc.lineas, key=lambda l: l.orden):
        cuenta_gasto = _resolver_cuenta_gasto(db, linea)
        if not cuenta_gasto:
            raise HTTPException(
                status_code=400,
                detail="No se pudo resolver la cuenta de gasto para una o más líneas"
            )
        cuenta_cxp = _resolver_cuenta_cxp(db, linea, fallback_cxp_id)
        if not cuenta_cxp:
            raise HTTPException(
                status_code=400,
                detail="No se pudo resolver la cuenta de proveedores para una o más líneas. "
                       "Verifica que el concepto tenga parametrizada la cuenta CxP, o configura "
                       "la cuenta global en Administración → Parámetros CxP."
            )

        add_linea(cuenta_gasto.id, linea.subtotal, Decimal("0"), linea.centro_costo_id)

        if linea.total_iva > 0 and linea.cuenta_iva_id:
            add_linea(linea.cuenta_iva_id, linea.total_iva, Decimal("0"))

        for ret in linea.retenciones:
            add_linea(ret.cuenta_id, Decimal("0"), ret.valor)

        # Crédito Proveedores = neto de esta línea
        ret_linea = sum(r.valor for r in linea.retenciones)
        neto = linea.subtotal + linea.total_iva - ret_linea
        add_linea(cuenta_cxp.id, Decimal("0"), neto)


def _get_fallback_cxp_id(db: Session) -> uuid.UUID | None:
    params = db.query(CxpParametroContable).first()
    return params.cuenta_proveedores_id if params else None


def _generar_asiento(db: Session, doc: CxpDocumento, actor: UsuarioActual) -> CntAsiento | None:
    moneda_func = _moneda_funcional(db)
    td_codigo = TIPO_A_CODIGO.get(doc.tipo, doc.tipo)
    td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == td_codigo).first()

    asiento = CntAsiento(
        id=uuid.uuid4(),
        tipo_documento_id=td.id if td else None,
        documento_numero=doc.numero,
        fecha=doc.fecha,
        periodo_id=doc.periodo_id,
        descripcion=f"{doc.tipo} {doc.numero} — {_get_tercero_nombre(db, doc.tercero_id)}",
        estado="borrador",
        moneda_id=doc.moneda_id,
        trm=doc.trm if doc.moneda_id != moneda_func.id else None,
        documento_origen_id=doc.id,
        documento_origen_tipo="cxp_documento",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(asiento)
    db.flush()
    fallback = _get_fallback_cxp_id(db)
    _poblar_lineas_asiento(db, asiento.id, doc, fallback, moneda_func)
    return asiento


def _calcular_totales_doc(doc: CxpDocumento) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum(l.subtotal for l in doc.lineas)
    total_iva = sum(l.total_iva for l in doc.lineas)
    total_ret = sum(r.valor for l in doc.lineas for r in l.retenciones)
    return subtotal, total_iva, total_ret


def _to_linea_response(db: Session, linea: CxpDocumentoLinea) -> CxpLineaResponse:
    concepto_nombre = None
    if linea.concepto_id:
        c = db.get(AdmConcepto, linea.concepto_id)
        concepto_nombre = c.nombre if c else None

    cuenta_codigo = cuenta_nombre = None
    if linea.cuenta_id:
        c = db.get(CntCuenta, linea.cuenta_id)
        if c:
            cuenta_codigo, cuenta_nombre = c.codigo, c.nombre

    cuenta_iva_codigo = None
    if linea.cuenta_iva_id:
        c = db.get(CntCuenta, linea.cuenta_iva_id)
        cuenta_iva_codigo = c.codigo if c else None

    rets = []
    for r in linea.retenciones:
        c = db.get(CntCuenta, r.cuenta_id)
        rets.append(LineaRetencionResponse(
            id=r.id, tipo=r.tipo, descripcion=r.descripcion,
            base=r.base, porcentaje=r.porcentaje, valor=r.valor,
            cuenta_id=r.cuenta_id,
            cuenta_codigo=c.codigo if c else None,
            cuenta_nombre=c.nombre if c else None,
        ))

    return CxpLineaResponse(
        id=linea.id, orden=linea.orden, descripcion=linea.descripcion,
        concepto_id=linea.concepto_id, concepto_nombre=concepto_nombre,
        cuenta_id=linea.cuenta_id, cuenta_codigo=cuenta_codigo, cuenta_nombre=cuenta_nombre,
        subtotal=linea.subtotal, iva_pct=linea.iva_pct,
        total_iva=linea.total_iva, total=linea.total,
        centro_costo_id=linea.centro_costo_id,
        iva_tipo=linea.iva_tipo,
        cuenta_iva_id=linea.cuenta_iva_id, cuenta_iva_codigo=cuenta_iva_codigo,
        retenciones=rets,
    )


def _to_response(doc: CxpDocumento, db: Session) -> CxpDocumentoResponse:
    tercero = db.get(AdmTercero, doc.tercero_id)
    moneda = db.get(AdmMoneda, doc.moneda_id)
    return CxpDocumentoResponse(
        id=doc.id, numero=doc.numero, tipo=doc.tipo,
        numero_proveedor=doc.numero_proveedor,
        fecha=doc.fecha, fecha_vencimiento=doc.fecha_vencimiento,
        periodo_id=doc.periodo_id,
        tercero_id=doc.tercero_id,
        tercero_nit=tercero.nit if tercero else None,
        tercero_nombre=tercero.razon_social if tercero else None,
        moneda_id=doc.moneda_id,
        moneda_codigo=moneda.codigo if moneda else "",
        trm=doc.trm,
        subtotal=doc.subtotal, total_iva=doc.total_iva,
        total_retenciones=doc.total_retenciones,
        total=doc.total, saldo=doc.saldo,
        descripcion=doc.descripcion,
        condicion_pago_id=doc.condicion_pago_id,
        ban_cuenta_id=doc.ban_cuenta_id,
        estado=doc.estado,
        asiento_id=doc.asiento_id,
        asiento_modificado_manual=doc.asiento_modificado_manual,
        documento_origen_id=doc.documento_origen_id,
        lineas=[_to_linea_response(db, l) for l in doc.lineas],
        creado_en=doc.creado_en,
        creado_por=doc.creado_por,
    )


def _to_list_item(doc: CxpDocumento, db: Session, hoy: date) -> CxpDocumentoListItem:
    tercero = db.get(AdmTercero, doc.tercero_id)
    moneda = db.get(AdmMoneda, doc.moneda_id)
    dias = None
    if doc.fecha_vencimiento and doc.estado == "contabilizado" and doc.saldo > 0:
        dias = (doc.fecha_vencimiento - hoy).days
    return CxpDocumentoListItem(
        id=doc.id, numero=doc.numero, tipo=doc.tipo,
        numero_proveedor=doc.numero_proveedor,
        fecha=doc.fecha, fecha_vencimiento=doc.fecha_vencimiento,
        tercero_nit=tercero.nit if tercero else None,
        tercero_nombre=tercero.razon_social if tercero else None,
        moneda_codigo=moneda.codigo if moneda else "",
        total=doc.total, saldo=doc.saldo,
        estado=doc.estado,
        dias_vencimiento=dias,
    )


def _persistir_lineas(db: Session, doc_id: uuid.UUID, lineas_data: list) -> None:
    for i, ld in enumerate(lineas_data, start=1):
        linea = CxpDocumentoLinea(
            id=uuid.uuid4(), documento_id=doc_id, orden=i,
            descripcion=ld.descripcion,
            concepto_id=ld.concepto_id, cuenta_id=ld.cuenta_id,
            subtotal=ld.subtotal, iva_pct=ld.iva_pct,
            total_iva=ld.total_iva, total=ld.total,
            centro_costo_id=ld.centro_costo_id,
            iva_tipo=f"GRAVADO_{int(ld.iva_pct)}" if ld.iva_tipo == "GRAVADO" else ld.iva_tipo,
            cuenta_iva_id=ld.cuenta_iva_id,
        )
        db.add(linea)
        db.flush()
        for ret in ld.retenciones:
            db.add(CxpLineaRetencion(
                id=uuid.uuid4(), linea_id=linea.id,
                tipo=ret.tipo, descripcion=ret.descripcion,
                base=ret.base, porcentaje=ret.porcentaje,
                valor=ret.valor, cuenta_id=ret.cuenta_id,
            ))


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def listar(
    db: Session,
    pagina: int = 1,
    por_pagina: int = 50,
    tipo: str | None = None,
    estado: str | None = None,
    tercero_id: uuid.UUID | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    solo_pendientes: bool = False,
) -> CxpListResponse:
    q = db.query(CxpDocumento).filter(CxpDocumento.activo == True)
    if tipo:          q = q.filter(CxpDocumento.tipo == tipo)
    if estado:        q = q.filter(CxpDocumento.estado == estado)
    if tercero_id:    q = q.filter(CxpDocumento.tercero_id == tercero_id)
    if fecha_desde:   q = q.filter(CxpDocumento.fecha >= fecha_desde)
    if fecha_hasta:   q = q.filter(CxpDocumento.fecha <= fecha_hasta)
    if solo_pendientes:
        q = q.filter(CxpDocumento.saldo > 0, CxpDocumento.estado == "contabilizado")

    total = q.count()
    hoy = date.today()
    rows = q.order_by(CxpDocumento.fecha.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    return CxpListResponse(
        items=[_to_list_item(r, db, hoy) for r in rows],
        total=total, pagina=pagina, por_pagina=por_pagina,
    )


def obtener(db: Session, id: uuid.UUID) -> CxpDocumentoResponse:
    doc = db.query(CxpDocumento).filter(CxpDocumento.id == id, CxpDocumento.activo == True).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return _to_response(doc, db)


def crear(db: Session, data: CxpDocumentoCreate, actor: UsuarioActual) -> CxpDocumentoResponse:
    periodo = _buscar_periodo(db, data.fecha)
    moneda_func = _moneda_funcional(db)

    if data.moneda_id != moneda_func.id and not data.trm:
        raise HTTPException(status_code=400, detail="Se requiere TRM para moneda extranjera")

    numero = _generar_numero(db, data.tipo)

    subtotal = sum(l.subtotal for l in data.lineas)
    total_iva = sum(l.total_iva for l in data.lineas)
    total_ret = sum(r.valor for l in data.lineas for r in l.retenciones)
    total = subtotal + total_iva - total_ret

    doc = CxpDocumento(
        id=uuid.uuid4(), numero=numero, tipo=data.tipo,
        numero_proveedor=data.numero_proveedor,
        fecha=data.fecha, fecha_vencimiento=data.fecha_vencimiento,
        condicion_pago_id=data.condicion_pago_id,
        periodo_id=periodo.id, tercero_id=data.tercero_id,
        moneda_id=data.moneda_id,
        trm=data.trm if data.moneda_id != moneda_func.id else None,
        subtotal=subtotal, total_iva=total_iva,
        total_retenciones=total_ret, total=total, saldo=total,
        descripcion=data.descripcion,
        estado="borrador",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(doc)
    db.flush()

    _persistir_lineas(db, doc.id, data.lineas)
    db.flush()
    db.refresh(doc)

    asiento = _generar_asiento(db, doc, actor)
    if asiento:
        doc.asiento_id = asiento.id

    db.commit()
    db.refresh(doc)
    return _to_response(doc, db)


def facturas_pendientes_cxp(
    db: Session,
    tercero_id: uuid.UUID,
    excluir_comprobante_id: uuid.UUID | None = None,
) -> list[FacturaPendienteCxpItem]:
    from sqlalchemy import func as sqlfunc
    hoy = date.today()
    docs = (
        db.query(CxpDocumento)
        .filter(
            CxpDocumento.activo == True,
            CxpDocumento.tercero_id == tercero_id,
            CxpDocumento.tipo == "FACTURA",
            CxpDocumento.estado == "contabilizado",
            CxpDocumento.saldo > 0,
        )
        .order_by(CxpDocumento.fecha_vencimiento.asc())
        .all()
    )
    result = []
    for d in docs:
        q = db.query(sqlfunc.coalesce(sqlfunc.sum(CxpAplicacion.valor), Decimal("0"))).filter(
            CxpAplicacion.documento_debito_id == d.id,
            CxpAplicacion.estado == "pendiente",
        )
        if excluir_comprobante_id:
            q = q.filter(CxpAplicacion.documento_credito_id != excluir_comprobante_id)
        pendiente = q.scalar()
        saldo_disp = d.saldo - pendiente
        if saldo_disp <= 0:
            continue
        dias = (d.fecha_vencimiento - hoy).days if d.fecha_vencimiento else None
        result.append(FacturaPendienteCxpItem(
            id=d.id, numero=d.numero, fecha=d.fecha,
            fecha_vencimiento=d.fecha_vencimiento,
            total=d.total, aplicado=(d.total - d.saldo) + pendiente,
            saldo=saldo_disp, dias_vencimiento=dias,
        ))
    return result


def aplicaciones_comprobante(db: Session, comprobante_id: uuid.UUID) -> list[AplicacionPendienteCxpItem]:
    apps = db.query(CxpAplicacion).filter(
        CxpAplicacion.documento_credito_id == comprobante_id,
        CxpAplicacion.estado.in_(["pendiente", "aplicado"]),
    ).all()
    result = []
    for ap in apps:
        fac = db.get(CxpDocumento, ap.documento_debito_id)
        if not fac:
            continue
        # pendiente → fac.saldo no fue reducido, es el saldo real disponible
        # aplicado  → fac.saldo ya fue reducido, hay que sumar ap.valor para reconstruir el original
        saldo_original = fac.saldo if ap.estado == "pendiente" else fac.saldo + ap.valor
        result.append(AplicacionPendienteCxpItem(
            id=ap.id, factura_id=fac.id, numero=fac.numero,
            fecha=fac.fecha, fecha_vencimiento=fac.fecha_vencimiento,
            total=fac.total,
            saldo_original=saldo_original,
            valor=ap.valor,
        ))
    return result


def _generar_asiento_comprobante(db: Session, doc: CxpDocumento, actor: UsuarioActual) -> CntAsiento | None:
    fallback_cxp_id = _get_fallback_cxp_id(db)
    if not fallback_cxp_id:
        return None
    cuenta_prov = db.get(CntCuenta, fallback_cxp_id)
    if not cuenta_prov:
        return None
    if not doc.ban_cuenta_id:
        return None
    ban_cuenta = db.get(BanCuenta, doc.ban_cuenta_id)
    if not ban_cuenta or not ban_cuenta.cuenta_contable_id:
        return None

    moneda_func = _moneda_funcional(db)
    trm = doc.trm or Decimal("1")
    td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "CP").first()

    asiento = CntAsiento(
        id=uuid.uuid4(),
        tipo_documento_id=td.id if td else None,
        documento_numero=doc.numero,
        fecha=doc.fecha,
        periodo_id=doc.periodo_id,
        descripcion=f"COMPROBANTE {doc.numero} — {_get_tercero_nombre(db, doc.tercero_id)}",
        estado="borrador",
        moneda_id=doc.moneda_id,
        trm=doc.trm if doc.moneda_id != moneda_func.id else None,
        documento_origen_id=doc.id,
        documento_origen_tipo="cxp_documento",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(asiento)
    db.flush()

    def add(cuenta_id, debito, credito):
        d_f = (debito * trm).quantize(Decimal("0.0001")) if doc.moneda_id != moneda_func.id else debito
        c_f = (credito * trm).quantize(Decimal("0.0001")) if doc.moneda_id != moneda_func.id else credito
        db.add(CntAsientoLinea(
            id=uuid.uuid4(), asiento_id=asiento.id, orden=1,
            cuenta_id=cuenta_id,
            debito=debito, credito=credito,
            debito_funcional=d_f, credito_funcional=c_f,
            tercero_id=doc.tercero_id,
        ))

    add(cuenta_prov.id, doc.total, Decimal("0"))
    add(ban_cuenta.cuenta_contable_id, Decimal("0"), doc.total)
    return asiento


def crear_comprobante(db: Session, data: ComprobanteCreate, actor: UsuarioActual) -> CxpDocumentoResponse:
    periodo = _buscar_periodo(db, data.fecha)
    moneda_func = _moneda_funcional(db)

    if data.moneda_id != moneda_func.id and not data.trm:
        raise HTTPException(status_code=400, detail="Se requiere TRM para moneda extranjera")

    ban_cuenta = db.get(BanCuenta, data.ban_cuenta_id)
    if not ban_cuenta or not ban_cuenta.activo:
        raise HTTPException(status_code=400, detail="Cuenta bancaria no encontrada")
    if not ban_cuenta.cuenta_contable_id:
        raise HTTPException(status_code=400, detail="La cuenta bancaria no tiene cuenta contable parametrizada")

    for ap in data.aplicaciones:
        fac = db.query(CxpDocumento).filter(
            CxpDocumento.id == ap.factura_id,
            CxpDocumento.activo == True,
            CxpDocumento.tipo == "FACTURA",
            CxpDocumento.estado == "contabilizado",
        ).first()
        if not fac:
            raise HTTPException(status_code=400, detail=f"Factura {ap.factura_id} no encontrada o no contabilizada")
        if fac.tercero_id != data.tercero_id:
            raise HTTPException(status_code=400, detail=f"La factura {fac.numero} no pertenece al proveedor seleccionado")
        pendiente_otros = db.query(
            __import__("sqlalchemy").func.coalesce(
                __import__("sqlalchemy").func.sum(CxpAplicacion.valor), Decimal("0")
            )
        ).filter(
            CxpAplicacion.documento_debito_id == ap.factura_id,
            CxpAplicacion.estado == "pendiente",
        ).scalar()
        if ap.valor > fac.saldo - pendiente_otros:
            raise HTTPException(status_code=400, detail=f"El valor supera el saldo disponible de la factura {fac.numero}")

    numero = _generar_numero(db, "COMPROBANTE")

    doc = CxpDocumento(
        id=uuid.uuid4(), numero=numero, tipo="COMPROBANTE",
        fecha=data.fecha, periodo_id=periodo.id,
        tercero_id=data.tercero_id, moneda_id=data.moneda_id,
        trm=data.trm if data.moneda_id != moneda_func.id else None,
        subtotal=data.valor_pagado,
        total_iva=Decimal("0"), total_retenciones=Decimal("0"),
        total=data.valor_pagado, saldo=data.valor_pagado,
        descripcion=data.descripcion,
        ban_cuenta_id=data.ban_cuenta_id,
        estado="borrador",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(doc)
    db.flush()

    for ap in data.aplicaciones:
        db.add(CxpAplicacion(
            id=uuid.uuid4(),
            documento_credito_id=doc.id,
            documento_debito_id=ap.factura_id,
            valor=ap.valor, fecha=data.fecha,
            estado="pendiente",
            creado_por=uuid.UUID(actor.id),
        ))

    db.flush()
    db.refresh(doc)

    asiento = _generar_asiento_comprobante(db, doc, actor)
    if asiento:
        doc.asiento_id = asiento.id

    db.commit()
    db.refresh(doc)
    return _to_response(doc, db)


def actualizar_comprobante(db: Session, comprobante_id: uuid.UUID, data: ComprobanteCreate, actor: UsuarioActual) -> CxpDocumentoResponse:
    doc = db.query(CxpDocumento).filter(CxpDocumento.id == comprobante_id, CxpDocumento.activo == True).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if doc.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se pueden editar comprobantes en borrador")

    periodo = _buscar_periodo(db, data.fecha)
    moneda_func = _moneda_funcional(db)

    ban_cuenta = db.get(BanCuenta, data.ban_cuenta_id)
    if not ban_cuenta or not ban_cuenta.activo:
        raise HTTPException(status_code=400, detail="Cuenta bancaria no encontrada")
    if not ban_cuenta.cuenta_contable_id:
        raise HTTPException(status_code=400, detail="La cuenta bancaria no tiene cuenta contable parametrizada")

    for ap in data.aplicaciones:
        fac = db.query(CxpDocumento).filter(
            CxpDocumento.id == ap.factura_id,
            CxpDocumento.activo == True,
            CxpDocumento.tipo == "FACTURA",
            CxpDocumento.estado == "contabilizado",
        ).first()
        if not fac:
            raise HTTPException(status_code=400, detail=f"Factura {ap.factura_id} no encontrada")
        if fac.tercero_id != data.tercero_id:
            raise HTTPException(status_code=400, detail=f"La factura {fac.numero} no pertenece al proveedor")
        app_actual = db.query(CxpAplicacion).filter(
            CxpAplicacion.documento_credito_id == comprobante_id,
            CxpAplicacion.documento_debito_id == ap.factura_id,
            CxpAplicacion.estado == "pendiente",
        ).first()
        saldo_disp = fac.saldo + (app_actual.valor if app_actual else Decimal("0"))
        if ap.valor > saldo_disp:
            raise HTTPException(status_code=400, detail=f"El valor supera el saldo de {fac.numero}")

    doc.fecha = data.fecha
    doc.periodo_id = periodo.id
    doc.tercero_id = data.tercero_id
    doc.moneda_id = data.moneda_id
    doc.trm = data.trm if data.moneda_id != moneda_func.id else None
    doc.subtotal = data.valor_pagado
    doc.total = data.valor_pagado
    doc.saldo = data.valor_pagado
    doc.descripcion = data.descripcion
    doc.ban_cuenta_id = data.ban_cuenta_id
    doc.modificado_por = uuid.UUID(actor.id)
    doc.modificado_en = datetime.now(timezone.utc)

    db.query(CxpAplicacion).filter(
        CxpAplicacion.documento_credito_id == comprobante_id,
        CxpAplicacion.estado == "pendiente",
    ).delete()
    for ap in data.aplicaciones:
        db.add(CxpAplicacion(
            id=uuid.uuid4(),
            documento_credito_id=doc.id,
            documento_debito_id=ap.factura_id,
            valor=ap.valor, fecha=data.fecha,
            estado="pendiente",
            creado_por=uuid.UUID(actor.id),
        ))

    db.flush()
    db.refresh(doc)

    asiento = db.get(CntAsiento, doc.asiento_id) if doc.asiento_id else None
    if asiento and asiento.estado == "borrador":
        moneda_func2 = _moneda_funcional(db)
        asiento.fecha = doc.fecha
        asiento.periodo_id = doc.periodo_id
        asiento.descripcion = f"COMPROBANTE {doc.numero} — {_get_tercero_nombre(db, doc.tercero_id)}"
        asiento.moneda_id = doc.moneda_id
        asiento.trm = doc.trm if doc.moneda_id != moneda_func2.id else None
        db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento.id).delete()
        db.flush()
        ban_cta = db.get(BanCuenta, doc.ban_cuenta_id)
        fallback = _get_fallback_cxp_id(db)
        cuenta_prov = db.get(CntCuenta, fallback) if fallback else None
        if cuenta_prov and ban_cta and ban_cta.cuenta_contable_id:
            trm = doc.trm or Decimal("1")
            for debito, credito, cta in [
                (doc.total, Decimal("0"), cuenta_prov.id),
                (Decimal("0"), doc.total, ban_cta.cuenta_contable_id),
            ]:
                d_f = (debito * trm).quantize(Decimal("0.0001")) if doc.moneda_id != moneda_func2.id else debito
                c_f = (credito * trm).quantize(Decimal("0.0001")) if doc.moneda_id != moneda_func2.id else credito
                db.add(CntAsientoLinea(
                    id=uuid.uuid4(), asiento_id=asiento.id, orden=1,
                    cuenta_id=cta, debito=debito, credito=credito,
                    debito_funcional=d_f, credito_funcional=c_f,
                    tercero_id=doc.tercero_id,
                ))
    else:
        nuevo = _generar_asiento_comprobante(db, doc, actor)
        if nuevo:
            doc.asiento_id = nuevo.id

    db.commit()
    db.refresh(doc)
    return _to_response(doc, db)


def resumen(db: Session, fecha_corte_str: str | None = None) -> CxpResumenResponse:
    from collections import defaultdict

    hoy = date.fromisoformat(fecha_corte_str) if fecha_corte_str else date.today()

    docs = db.query(CxpDocumento).filter(
        CxpDocumento.activo == True,
        CxpDocumento.estado == "contabilizado",
        CxpDocumento.saldo > 0,
        CxpDocumento.tipo == "FACTURA",
    ).all()

    buckets: dict = defaultdict(lambda: {
        "corriente": Decimal("0"), "dias_1_30": Decimal("0"),
        "dias_31_60": Decimal("0"), "dias_61_90": Decimal("0"), "mas_90": Decimal("0"),
    })

    for doc in docs:
        b = buckets[doc.tercero_id]
        if doc.fecha_vencimiento is None or doc.fecha_vencimiento >= hoy:
            b["corriente"] += doc.saldo
        else:
            dias = (hoy - doc.fecha_vencimiento).days
            if dias <= 30:   b["dias_1_30"]  += doc.saldo
            elif dias <= 60: b["dias_31_60"] += doc.saldo
            elif dias <= 90: b["dias_61_90"] += doc.saldo
            else:            b["mas_90"]     += doc.saldo

    items = []
    tot = {"corriente": Decimal("0"), "dias_1_30": Decimal("0"),
           "dias_31_60": Decimal("0"), "dias_61_90": Decimal("0"), "mas_90": Decimal("0")}

    for tercero_id, b in buckets.items():
        tercero = db.get(AdmTercero, tercero_id)
        total = sum(b.values())
        items.append(CxpResumenItem(
            tercero_id=tercero_id,
            tercero_nit=tercero.nit if tercero else None,
            tercero_nombre=tercero.razon_social if tercero else None,
            corriente=b["corriente"], dias_1_30=b["dias_1_30"],
            dias_31_60=b["dias_31_60"], dias_61_90=b["dias_61_90"],
            mas_90=b["mas_90"], total=total,
        ))
        for k in tot: tot[k] += b[k]

    items.sort(key=lambda x: x.mas_90 + x.dias_61_90 + x.dias_31_60, reverse=True)

    return CxpResumenResponse(
        fecha_corte=hoy, items=items,
        total_corriente=tot["corriente"], total_1_30=tot["dias_1_30"],
        total_31_60=tot["dias_31_60"], total_61_90=tot["dias_61_90"],
        total_mas_90=tot["mas_90"],
        total_general=sum(tot.values()),
    )


def resumen_excel(db: Session, fecha_corte_str: str | None = None):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    data = resumen(db, fecha_corte_str)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Saldos Proveedores"

    thin = Side(style="thin", color="AAAAAA")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_font = Font(bold=True, size=10)
    title_font  = Font(bold=True, size=12)
    num_fmt = '#,##0'

    ws.merge_cells("A1:H1")
    ws["A1"] = f"Saldos de Proveedores — Fecha de corte: {data.fecha_corte}"
    ws["A1"].font = title_font

    headers = ["NIT", "Proveedor", "Corriente", "1 – 30 días", "31 – 60 días", "61 – 90 días", "+ 90 días", "Total"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    for row_idx, item in enumerate(data.items, 4):
        vals = [
            item.tercero_nit or "",
            item.tercero_nombre or "",
            float(item.corriente),
            float(item.dias_1_30),
            float(item.dias_31_60),
            float(item.dias_61_90),
            float(item.mas_90),
            float(item.total),
        ]
        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = border
            if col >= 3:
                cell.number_format = num_fmt
                cell.alignment = Alignment(horizontal="right")

    total_row = len(data.items) + 4
    totals = ["TOTAL", "",
              float(data.total_corriente), float(data.total_1_30),
              float(data.total_31_60), float(data.total_61_90),
              float(data.total_mas_90), float(data.total_general)]
    fill = PatternFill(fill_type="solid", fgColor="EEEEEE")
    for col, val in enumerate(totals, 1):
        cell = ws.cell(row=total_row, column=col, value=val)
        cell.font = Font(bold=True, size=10)
        cell.fill = fill
        cell.border = border
        if col >= 3:
            cell.number_format = num_fmt
            cell.alignment = Alignment(horizontal="right")

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 36
    for col in ["C", "D", "E", "F", "G", "H"]:
        ws.column_dimensions[col].width = 16

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"saldos_cxp_{data.fecha_corte}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def actualizar(db: Session, id: uuid.UUID, data: CxpDocumentoUpdate, actor: UsuarioActual) -> CxpDocumentoResponse:
    doc = db.query(CxpDocumento).filter(CxpDocumento.id == id, CxpDocumento.activo == True).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if doc.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se pueden editar documentos en borrador")

    if data.fecha is not None:
        periodo = _buscar_periodo(db, data.fecha)
        doc.fecha = data.fecha
        doc.periodo_id = periodo.id
    if data.fecha_vencimiento is not None: doc.fecha_vencimiento = data.fecha_vencimiento
    if data.condicion_pago_id is not None: doc.condicion_pago_id = data.condicion_pago_id
    if data.numero_proveedor is not None:  doc.numero_proveedor = data.numero_proveedor
    if data.tercero_id is not None:        doc.tercero_id = data.tercero_id
    if data.moneda_id is not None:         doc.moneda_id = data.moneda_id
    if data.trm is not None:               doc.trm = data.trm
    if data.descripcion is not None:       doc.descripcion = data.descripcion

    if data.lineas is not None:
        db.query(CxpDocumentoLinea).filter(CxpDocumentoLinea.documento_id == id).delete()
        db.flush()
        _persistir_lineas(db, doc.id, data.lineas)
        db.flush()
        db.refresh(doc)

        subtotal = sum(l.subtotal for l in doc.lineas)
        total_iva = sum(l.total_iva for l in doc.lineas)
        total_ret = sum(r.valor for l in doc.lineas for r in l.retenciones)
        total = subtotal + total_iva - total_ret
        doc.subtotal = subtotal
        doc.total_iva = total_iva
        doc.total_retenciones = total_ret
        doc.total = total
        doc.saldo = total

    doc.modificado_por = uuid.UUID(actor.id)
    doc.modificado_en = datetime.now(timezone.utc)

    # Regenerar asiento borrador
    if doc.asiento_id:
        asiento = db.get(CntAsiento, doc.asiento_id)
        if asiento and asiento.estado == "borrador":
            moneda_func = _moneda_funcional(db)
            asiento.fecha = doc.fecha
            asiento.periodo_id = doc.periodo_id
            asiento.descripcion = f"{doc.tipo} {doc.numero} — {_get_tercero_nombre(db, doc.tercero_id)}"
            db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento.id).delete()
            db.flush()
            _poblar_lineas_asiento(db, asiento.id, doc, _get_fallback_cxp_id(db), moneda_func)
    else:
        asiento = _generar_asiento(db, doc, actor)
        if asiento:
            doc.asiento_id = asiento.id

    db.commit()
    db.refresh(doc)
    return _to_response(doc, db)


def contabilizar(db: Session, id: uuid.UUID, actor: UsuarioActual) -> CxpDocumentoResponse:
    doc = db.query(CxpDocumento).filter(CxpDocumento.id == id, CxpDocumento.activo == True).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if doc.estado != "borrador":
        raise HTTPException(status_code=409, detail="El documento ya está contabilizado o anulado")

    periodo = db.get(CntPeriodo, doc.periodo_id)
    if not periodo or periodo.estado != "abierto":
        raise HTTPException(status_code=400, detail="El período contable no está abierto")
    if doc.total <= 0:
        raise HTTPException(status_code=400, detail="El total del documento debe ser mayor que cero")
    if doc.tipo in ("FACTURA", "NOTA_DEBITO") and not doc.fecha_vencimiento:
        raise HTTPException(status_code=400, detail="La fecha de vencimiento es obligatoria")
    # COMPROBANTE: procesar aplicaciones pendientes
    if doc.tipo == "COMPROBANTE":
        apps = db.query(CxpAplicacion).filter(
            CxpAplicacion.documento_credito_id == id,
            CxpAplicacion.estado == "pendiente",
        ).all()
        if not apps:
            raise HTTPException(status_code=400, detail="El comprobante no tiene facturas aplicadas")
        for ap in apps:
            fac = db.query(CxpDocumento).filter(
                CxpDocumento.id == ap.documento_debito_id,
                CxpDocumento.activo == True,
            ).with_for_update().first()
            if not fac:
                raise HTTPException(status_code=400, detail="Factura aplicada no encontrada")
            if ap.valor > fac.saldo:
                raise HTTPException(status_code=400, detail=f"El saldo de {fac.numero} cambió. Revisa el comprobante.")
            fac.saldo -= ap.valor
            ap.estado = "aplicado"
        doc.saldo = Decimal("0")

        # Generar/regenerar asiento comprobante
        if not doc.asiento_id:
            asiento_cp = _generar_asiento_comprobante(db, doc, actor)
            if not asiento_cp:
                raise HTTPException(
                    status_code=400,
                    detail="Configura la cuenta de proveedores en Parámetros CxP y la cuenta contable en la cuenta bancaria."
                )
            doc.asiento_id = asiento_cp.id
            db.flush()

        asiento = db.get(CntAsiento, doc.asiento_id)
        if not asiento or asiento.estado != "borrador":
            raise HTTPException(status_code=409, detail="El asiento ya está publicado o no fue encontrado")

        ban_cuenta = db.get(BanCuenta, doc.ban_cuenta_id)
        fallback = _get_fallback_cxp_id(db)
        cuenta_prov = db.get(CntCuenta, fallback) if fallback else None
        moneda_func = _moneda_funcional(db)
        if not cuenta_prov or not ban_cuenta or not ban_cuenta.cuenta_contable_id:
            raise HTTPException(status_code=400, detail="Parametriza cuenta proveedores y cuenta contable bancaria")

        trm = doc.trm or Decimal("1")
        asiento.fecha = doc.fecha
        asiento.periodo_id = doc.periodo_id
        asiento.descripcion = f"COMPROBANTE {doc.numero} — {_get_tercero_nombre(db, doc.tercero_id)}"
        asiento.moneda_id = doc.moneda_id
        asiento.trm = doc.trm if doc.moneda_id != moneda_func.id else None
        db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento.id).delete()
        db.flush()
        for debito, credito, cta in [
            (doc.total, Decimal("0"), cuenta_prov.id),
            (Decimal("0"), doc.total, ban_cuenta.cuenta_contable_id),
        ]:
            d_f = (debito * trm).quantize(Decimal("0.0001")) if doc.moneda_id != moneda_func.id else debito
            c_f = (credito * trm).quantize(Decimal("0.0001")) if doc.moneda_id != moneda_func.id else credito
            db.add(CntAsientoLinea(
                id=uuid.uuid4(), asiento_id=asiento.id, orden=1,
                cuenta_id=cta, debito=debito, credito=credito,
                debito_funcional=d_f, credito_funcional=c_f,
                tercero_id=doc.tercero_id,
            ))
        db.flush()
        lineas = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento.id).all()
        total_d = sum(l.debito for l in lineas)
        total_c = sum(l.credito for l in lineas)
        if abs(total_d - total_c) > Decimal("0.01"):
            raise HTTPException(status_code=400, detail=f"Asiento descuadrado ({total_d} ≠ {total_c})")
        asiento.estado = "publicado"
        asiento.modificado_por = uuid.UUID(actor.id)
        asiento.modificado_en = datetime.now(timezone.utc)
        doc.estado = "contabilizado"
        doc.modificado_por = uuid.UUID(actor.id)
        doc.modificado_en = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)
        return _to_response(doc, db)

    for linea in doc.lineas:
        for ret in linea.retenciones:
            if not ret.cuenta_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"La retención '{ret.descripcion or ret.tipo}' no tiene cuenta contable asignada"
                )
        cuenta_gasto = _resolver_cuenta_gasto(db, linea)
        if cuenta_gasto:
            if cuenta_gasto.requiere_cc and not linea.centro_costo_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"La cuenta {cuenta_gasto.codigo} — {cuenta_gasto.nombre} requiere centro de costo en la línea '{linea.descripcion or linea.orden}'"
                )
            if cuenta_gasto.requiere_tercero and not doc.tercero_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"La cuenta {cuenta_gasto.codigo} — {cuenta_gasto.nombre} requiere tercero"
                )

    moneda_func = _moneda_funcional(db)
    fallback_cxp_id = _get_fallback_cxp_id(db)

    if not doc.asiento_id:
        asiento = _generar_asiento(db, doc, actor)
        if not asiento:
            raise HTTPException(status_code=400, detail="No se pudo generar el asiento contable")
        doc.asiento_id = asiento.id
        db.flush()

    asiento = db.get(CntAsiento, doc.asiento_id)
    if not asiento:
        raise HTTPException(status_code=400, detail="El asiento contable no fue encontrado")
    if asiento.estado != "borrador":
        raise HTTPException(status_code=409, detail="El asiento ya está publicado")

    # Regenerar líneas desde datos actuales
    asiento.fecha = doc.fecha
    asiento.periodo_id = doc.periodo_id
    asiento.descripcion = f"{doc.tipo} {doc.numero} — {_get_tercero_nombre(db, doc.tercero_id)}"
    asiento.moneda_id = doc.moneda_id
    asiento.trm = doc.trm if doc.moneda_id != moneda_func.id else None
    db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento.id).delete()
    db.flush()
    _poblar_lineas_asiento(db, asiento.id, doc, fallback_cxp_id, moneda_func)
    db.flush()

    lineas = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento.id).all()
    total_d = sum(l.debito for l in lineas)
    total_c = sum(l.credito for l in lineas)
    if abs(total_d - total_c) > Decimal("0.01"):
        raise HTTPException(
            status_code=400,
            detail=f"El asiento está descuadrado (débitos {total_d} ≠ créditos {total_c})"
        )

    asiento.estado = "publicado"
    asiento.modificado_por = uuid.UUID(actor.id)
    asiento.modificado_en = datetime.now(timezone.utc)

    doc.estado = "contabilizado"
    doc.saldo = doc.total
    doc.modificado_por = uuid.UUID(actor.id)
    doc.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(doc)
    return _to_response(doc, db)


def anular(db: Session, id: uuid.UUID, data: AnularCxpRequest, actor: UsuarioActual) -> CxpDocumentoResponse:
    doc = db.query(CxpDocumento).filter(CxpDocumento.id == id, CxpDocumento.activo == True).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if doc.estado == "anulado":
        raise HTTPException(status_code=409, detail="El documento ya está anulado")

    # Verificar aplicaciones (comprobantes de pago aplicados)
    apps = db.query(CxpAplicacion).filter(
        CxpAplicacion.documento_debito_id == id,
    ).first()
    if apps:
        raise HTTPException(
            status_code=409,
            detail="La factura tiene comprobantes de pago aplicados. Revierta el pago antes de anular."
        )

    # Si está contabilizada: verificar período y generar contraasiento
    if doc.estado == "contabilizado":
        periodo = db.get(CntPeriodo, doc.periodo_id)
        if not periodo or periodo.estado != "abierto":
            raise HTTPException(status_code=400, detail="El período contable no está abierto")

        if doc.asiento_id:
            asiento_orig = db.get(CntAsiento, doc.asiento_id)
            if asiento_orig:
                lineas_orig = db.query(CntAsientoLinea).filter(
                    CntAsientoLinea.asiento_id == asiento_orig.id
                ).all()

                contraasiento = CntAsiento(
                    id=uuid.uuid4(),
                    tipo_documento_id=asiento_orig.tipo_documento_id,
                    documento_numero=asiento_orig.documento_numero,
                    fecha=date.today(),
                    periodo_id=doc.periodo_id,
                    descripcion=f"ANULACIÓN {doc.tipo} {doc.numero} — {_get_tercero_nombre(db, doc.tercero_id)} · {data.motivo}",
                    estado="publicado",
                    moneda_id=asiento_orig.moneda_id,
                    trm=asiento_orig.trm,
                    documento_origen_id=doc.id,
                    documento_origen_tipo="cxp_documento",
                    creado_por=uuid.UUID(actor.id),
                )
                db.add(contraasiento)
                db.flush()

                for i, linea in enumerate(lineas_orig, start=1):
                    db.add(CntAsientoLinea(
                        id=uuid.uuid4(),
                        asiento_id=contraasiento.id,
                        orden=i,
                        cuenta_id=linea.cuenta_id,
                        debito=linea.credito,
                        credito=linea.debito,
                        debito_funcional=linea.credito_funcional,
                        credito_funcional=linea.debito_funcional,
                        tercero_id=linea.tercero_id,
                        centro_costo_id=linea.centro_costo_id,
                        descripcion=data.motivo,
                    ))

    elif doc.estado == "borrador" and doc.asiento_id:
        # Borrador: solo eliminar el asiento borrador
        asiento_borrador = db.get(CntAsiento, doc.asiento_id)
        if asiento_borrador and asiento_borrador.estado == "borrador":
            db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento_borrador.id).delete()
            db.delete(asiento_borrador)
            doc.asiento_id = None

    doc.estado = "anulado"
    doc.saldo = Decimal("0")
    doc.modificado_por = uuid.UUID(actor.id)
    doc.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc)
    return _to_response(doc, db)
