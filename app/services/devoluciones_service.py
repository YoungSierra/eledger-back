"""Devoluciones en ventas.

Una devolución nace de una factura de venta contabilizada. Genera SIEMPRE una
nota crédito de CxC (tipo NOTA_CREDITO) que cruza contra la factura afectada y
queda lista para transmitir a la DIAN. Efectos al contabilizar:

  1. Asiento de la NC (reversa de la factura por las líneas devueltas):
       Dr Devolución en ventas (cascada de cuenta)   subtotal
       Dr IVA (misma cuenta que la factura)           total_iva
       Cr Clientes                                    total
  2. Documento CxC NOTA_CREDITO + CxcAplicacion que reduce el saldo de la factura.
  3. Solo para líneas de PRODUCTO: entrada de inventario (DEVOLUCION_CLIENTE) al
     costo original de venta, con su propio asiento Dr Inventario / Cr Costo de ventas.

Las líneas de CONCEPTO (servicios de cotización) no tocan inventario: son solo el
puente hacia la nota crédito. Las líneas de valor recibido para tercero (VRT) no
son devolvibles por esta vía (implicarían reversar el CxP del tercero).
"""
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.admin import AdmMoneda, AdmTipoDocumento
from app.models.adm import AdmTercero
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntCentroCosto, CntCuenta, CntPeriodo
from app.models.cxc import CxcDocumento, CxcAplicacion, CxcParametroContable
from app.models.facturacion import (
    FacFactura, FacFacturaLinea, FacDevolucion, FacDevolucionLinea, FacDevolucionRetencion,
)
from app.models.inventario import (
    InvProducto, InvProductoUm, InvProductoBodega, InvMovimiento, InvMovimientoLinea,
    InvRemisionLinea,
)
from app.models.ope import OpeCotizacionLinea, OpeConcepto
from app.schemas.auth import UsuarioActual
from app.schemas.devoluciones import (
    DevolucionCreate, DevolucionUpdate, AnularDevolucionRequest,
    DevolucionResponse, DevolucionLineaResponse,
    DevolucionListItem, DevolucionListResponse,
    DevPreviewResponse, DevPreviewLinea,
)

TIPO_NC = "NOTA_CREDITO"
CODIGO_NC = "NCC"
TOL = Decimal("0.0001")
Q = Decimal("0.0001")


# ---------------------------------------------------------------------------
# Helpers de cálculo
# ---------------------------------------------------------------------------

def _moneda_funcional(db: Session) -> AdmMoneda:
    m = db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.activo == True).first()
    if not m:
        raise HTTPException(status_code=400, detail="No hay moneda funcional configurada")
    return m


def _buscar_periodo(db: Session, fecha: date) -> CntPeriodo:
    p = db.query(CntPeriodo).filter(
        CntPeriodo.fecha_inicio <= fecha,
        CntPeriodo.fecha_cierre >= fecha,
        CntPeriodo.activo == True,
    ).first()
    if not p:
        raise HTTPException(status_code=400, detail=f"No existe período contable para la fecha {fecha}")
    return p


def _factor_um(db: Session, producto: InvProducto, um_id) -> Decimal:
    if not um_id or um_id == producto.um_base_id:
        return Decimal("1")
    pu = db.query(InvProductoUm).filter(
        InvProductoUm.producto_id == producto.id, InvProductoUm.um_id == um_id,
    ).first()
    return Decimal(str(pu.factor)) if pu and pu.factor else Decimal("1")


def _devuelto_por_linea(db: Session, factura_id: uuid.UUID, excluir_dev_id: uuid.UUID | None = None) -> dict:
    """Cantidad ya devuelta por cada línea de factura (devoluciones no anuladas)."""
    q = (
        db.query(FacDevolucionLinea.factura_linea_id, func.coalesce(func.sum(FacDevolucionLinea.cantidad), 0))
        .join(FacDevolucion, FacDevolucionLinea.devolucion_id == FacDevolucion.id)
        .filter(FacDevolucion.factura_id == factura_id, FacDevolucion.estado != "anulado")
    )
    if excluir_dev_id:
        q = q.filter(FacDevolucion.id != excluir_dev_id)
    return {lid: Decimal(str(c or 0)) for lid, c in q.group_by(FacDevolucionLinea.factura_linea_id).all()}


def _es_producto(fl: FacFacturaLinea) -> bool:
    return fl.producto_id is not None


def _concepto_de_factura_linea(db: Session, fl: FacFacturaLinea) -> OpeConcepto | None:
    if not fl.cotizacion_linea_id:
        return None
    cl = db.get(OpeCotizacionLinea, fl.cotizacion_linea_id)
    if cl and cl.concepto_id:
        return db.get(OpeConcepto, cl.concepto_id)
    return None


def _resolver_cuenta_devolucion(db: Session, fl: FacFacturaLinea, params: CxcParametroContable | None) -> CntCuenta | None:
    """Cascada de la cuenta de devolución en ventas:
    - Producto: producto → familia → tipo → parámetro CxC (respaldo).
    - Concepto: concepto → parámetro CxC (respaldo)."""
    from app.services.inventario_service import _resolver_cuenta_ajuste
    if _es_producto(fl):
        prod = db.get(InvProducto, fl.producto_id)
        if prod:
            cta = _resolver_cuenta_ajuste(db, prod, "cuenta_devolucion_venta_id")
            if cta:
                return cta
    else:
        concepto = _concepto_de_factura_linea(db, fl)
        if concepto and concepto.cuenta_devolucion_venta_id:
            return db.get(CntCuenta, concepto.cuenta_devolucion_venta_id)
    if params and params.cuenta_devolucion_venta_id:
        return db.get(CntCuenta, params.cuenta_devolucion_venta_id)
    return None


def _resolver_cuenta_iva(db: Session, fl: FacFacturaLinea, params: CxcParametroContable | None) -> CntCuenta | None:
    if fl.cuenta_iva_id:
        return db.get(CntCuenta, fl.cuenta_iva_id)
    if params and params.cuenta_iva_id:
        return db.get(CntCuenta, params.cuenta_iva_id)
    return None


def _prorratear(fl: FacFacturaLinea, cantidad: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """Prorratea subtotal/IVA/total de la línea de factura según la cantidad devuelta.
    Prorratea sobre el neto (respeta descuentos aplicados en la factura)."""
    fcant = Decimal(str(fl.cantidad))
    if fcant <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    frac = cantidad / fcant
    subtotal = (Decimal(str(fl.subtotal)) * frac).quantize(Q)
    total_iva = (Decimal(str(fl.total_iva)) * frac).quantize(Q)
    return subtotal, total_iva, (subtotal + total_iva)


def _construir_lineas(db: Session, factura: FacFactura, data_lineas, excluir_dev_id=None):
    """Valida y arma las líneas de la devolución. Retorna lista de dicts."""
    devuelto = _devuelto_por_linea(db, factura.id, excluir_dev_id)
    fmap = {l.id: l for l in factura.lineas}
    out = []
    for orden, dl in enumerate(data_lineas, start=1):
        fl = fmap.get(dl.factura_linea_id)
        if not fl:
            raise HTTPException(status_code=400, detail="Una línea no pertenece a la factura indicada")
        if fl.valor_tercero:
            raise HTTPException(status_code=400,
                detail=f"La línea '{fl.descripcion}' es un valor para tercero y no se devuelve por esta vía.")
        cant = Decimal(str(dl.cantidad))
        if cant <= 0:
            continue
        pendiente = Decimal(str(fl.cantidad)) - devuelto.get(fl.id, Decimal("0"))
        if cant - pendiente > TOL:
            raise HTTPException(status_code=400,
                detail=f"La cantidad a devolver de '{fl.descripcion}' excede lo pendiente ({pendiente}).")
        subtotal, total_iva, total = _prorratear(fl, cant)
        out.append({
            "orden": orden,
            "factura_linea_id": fl.id,
            "producto_id": fl.producto_id,
            "descripcion": fl.descripcion,
            "cantidad": cant,
            "precio_unitario": Decimal(str(fl.precio_unitario)),
            "subtotal": subtotal,
            "iva_tipo": fl.iva_tipo,
            "iva_pct": Decimal(str(fl.iva_pct)),
            "total_iva": total_iva,
            "total": total,
            "cuenta_iva_id": fl.cuenta_iva_id,
            "centro_costo_id": fl.centro_costo_id,
            "_fl": fl,
        })
    if not out:
        raise HTTPException(status_code=400, detail="Indica al menos una línea con cantidad a devolver")
    return out


# ---------------------------------------------------------------------------
# Serialización
# ---------------------------------------------------------------------------

def _to_linea_response(db: Session, l: FacDevolucionLinea, factura: FacFactura | None) -> DevolucionLineaResponse:
    prod_cod = prod_nom = None
    if l.producto_id:
        p = db.get(InvProducto, l.producto_id)
        if p:
            prod_cod, prod_nom = p.codigo, p.nombre
    cta_cod = cta_nom = None
    if l.cuenta_devolucion_id:
        c = db.get(CntCuenta, l.cuenta_devolucion_id)
        if c:
            cta_cod, cta_nom = c.codigo, c.nombre
    cant_fact = None
    if factura:
        fl = next((x for x in factura.lineas if x.id == l.factura_linea_id), None)
        cant_fact = fl.cantidad if fl else None
    return DevolucionLineaResponse(
        id=l.id, orden=l.orden, factura_linea_id=l.factura_linea_id,
        producto_id=l.producto_id, producto_codigo=prod_cod, producto_nombre=prod_nom,
        descripcion=l.descripcion, cantidad=l.cantidad, cantidad_facturada=cant_fact,
        precio_unitario=l.precio_unitario, subtotal=l.subtotal,
        iva_tipo=l.iva_tipo, iva_pct=l.iva_pct, total_iva=l.total_iva, total=l.total,
        cuenta_devolucion_id=l.cuenta_devolucion_id,
        cuenta_devolucion_codigo=cta_cod, cuenta_devolucion_nombre=cta_nom,
        cuenta_iva_id=l.cuenta_iva_id, centro_costo_id=l.centro_costo_id,
        es_producto=l.producto_id is not None,
    )


def _to_response(db: Session, dev: FacDevolucion) -> DevolucionResponse:
    factura = db.get(FacFactura, dev.factura_id)
    cliente = db.get(AdmTercero, dev.cliente_id)
    moneda = db.get(AdmMoneda, dev.moneda_id)
    return DevolucionResponse(
        id=dev.id, numero=dev.numero,
        factura_id=dev.factura_id, factura_numero=factura.numero if factura else None,
        fecha=dev.fecha, motivo=dev.motivo, concepto_dian=dev.concepto_dian,
        periodo_id=dev.periodo_id,
        cliente_id=dev.cliente_id,
        cliente_nit=cliente.nit if cliente else None,
        cliente_nombre=cliente.razon_social if cliente else None,
        moneda_id=dev.moneda_id, moneda_codigo=moneda.codigo if moneda else "",
        trm=dev.trm,
        subtotal=dev.subtotal, total_iva=dev.total_iva, total=dev.total,
        descripcion=dev.descripcion, estado=dev.estado,
        asiento_id=dev.asiento_id, cxc_documento_id=dev.cxc_documento_id,
        cune=dev.cune, dian_estado=dev.dian_estado,
        lineas=[_to_linea_response(db, l, factura) for l in dev.lineas],
        creado_en=dev.creado_en, creado_por=dev.creado_por,
    )


def _to_list_item(db: Session, dev: FacDevolucion) -> DevolucionListItem:
    factura = db.get(FacFactura, dev.factura_id)
    cliente = db.get(AdmTercero, dev.cliente_id)
    moneda = db.get(AdmMoneda, dev.moneda_id)
    return DevolucionListItem(
        id=dev.id, numero=dev.numero, fecha=dev.fecha,
        factura_id=dev.factura_id, factura_numero=factura.numero if factura else None,
        cliente_nombre=cliente.razon_social if cliente else None,
        moneda_codigo=moneda.codigo if moneda else "",
        subtotal=dev.subtotal, total_iva=dev.total_iva, total=dev.total,
        estado=dev.estado, dian_estado=dev.dian_estado, creado_en=dev.creado_en,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def _factura_contab(db: Session, factura_id: uuid.UUID) -> FacFactura:
    fac = db.query(FacFactura).filter(FacFactura.id == factura_id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if fac.estado != "contabilizada":
        raise HTTPException(status_code=409, detail="Solo se puede devolver sobre una factura contabilizada")
    return fac


def listar(db: Session, pagina: int = 1, por_pagina: int = 50,
           estado: str | None = None, factura_id: uuid.UUID | None = None) -> DevolucionListResponse:
    q = db.query(FacDevolucion).filter(FacDevolucion.activo == True)
    if estado:      q = q.filter(FacDevolucion.estado == estado)
    if factura_id:  q = q.filter(FacDevolucion.factura_id == factura_id)
    total = q.count()
    rows = (q.order_by(FacDevolucion.fecha.desc(), FacDevolucion.creado_en.desc())
            .offset((pagina - 1) * por_pagina).limit(por_pagina).all())
    return DevolucionListResponse(
        items=[_to_list_item(db, r) for r in rows],
        total=total, pagina=pagina, por_pagina=por_pagina,
    )


def obtener(db: Session, id: uuid.UUID) -> DevolucionResponse:
    dev = db.query(FacDevolucion).filter(FacDevolucion.id == id, FacDevolucion.activo == True).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    return _to_response(db, dev)


def _persistir_retenciones(db: Session, dev: FacDevolucion, factura, subtotal_dev: Decimal) -> Decimal:
    """Reversa las retenciones de la factura en proporción a lo devuelto.

    La proporción se toma sobre el SUBTOTAL, que es la base sobre la que se
    calcularon. Devolver el 40% del subtotal reversa el 40% de cada retención.

    La última línea absorbe el redondeo para que la suma cuadre exactamente con
    la proporción del total: si se reparte por línea, tres redondeos hacia abajo
    dejan el asiento descuadrado por centavos.
    """
    db.query(FacDevolucionRetencion).filter(
        FacDevolucionRetencion.devolucion_id == dev.id).delete()

    rets = list(factura.retenciones or [])
    base_factura = Decimal(str(factura.subtotal or 0))
    if not rets or base_factura <= 0 or subtotal_dev <= 0:
        return Decimal("0")

    frac = subtotal_dev / base_factura
    if frac > 1:
        frac = Decimal("1")

    objetivo = (sum(Decimal(str(r.valor)) for r in rets) * frac).quantize(Q)
    acumulado = Decimal("0")
    for i, r in enumerate(rets):
        if i == len(rets) - 1:
            valor = objetivo - acumulado
        else:
            valor = (Decimal(str(r.valor)) * frac).quantize(Q)
            acumulado += valor
        db.add(FacDevolucionRetencion(
            id=uuid.uuid4(), devolucion_id=dev.id,
            tipo=r.tipo, concepto=r.concepto,
            base=(Decimal(str(r.base)) * frac).quantize(Q),
            porcentaje=r.porcentaje, valor=valor, cuenta_id=r.cuenta_id,
        ))
    return objetivo


def _persistir_lineas(db: Session, dev: FacDevolucion, lineas: list[dict], params) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    subtotal = total_iva = Decimal("0")
    for l in lineas:
        cta_dev = _resolver_cuenta_devolucion(db, l["_fl"], params)
        db.add(FacDevolucionLinea(
            id=uuid.uuid4(), devolucion_id=dev.id, orden=l["orden"],
            factura_linea_id=l["factura_linea_id"], producto_id=l["producto_id"],
            descripcion=l["descripcion"], cantidad=l["cantidad"],
            precio_unitario=l["precio_unitario"], subtotal=l["subtotal"],
            iva_tipo=l["iva_tipo"], iva_pct=l["iva_pct"], total_iva=l["total_iva"], total=l["total"],
            cuenta_devolucion_id=cta_dev.id if cta_dev else None,
            cuenta_iva_id=l["cuenta_iva_id"], centro_costo_id=l["centro_costo_id"],
        ))
        subtotal += l["subtotal"]
        total_iva += l["total_iva"]

    factura = db.get(FacFactura, dev.factura_id)
    db.flush()   # la devolución debe existir antes de colgarle retenciones
    total_ret = _persistir_retenciones(db, dev, factura, subtotal) if factura else Decimal("0")
    # `total` es NETO, igual que en la factura: es lo que se le abona al cliente.
    return subtotal, total_iva, total_ret, (subtotal + total_iva - total_ret)


def crear(db: Session, data: DevolucionCreate, actor: UsuarioActual) -> DevolucionResponse:
    factura = _factura_contab(db, data.factura_id)
    if not data.lineas:
        raise HTTPException(status_code=400, detail="La devolución debe tener al menos una línea")
    params = db.query(CxcParametroContable).first()
    lineas = _construir_lineas(db, factura, data.lineas)
    periodo = _buscar_periodo(db, data.fecha)
    from app.services import cxc_service
    numero = cxc_service._generar_o_validar_numero(db, TIPO_NC, None)

    dev = FacDevolucion(
        id=uuid.uuid4(), numero=numero, factura_id=factura.id,
        fecha=data.fecha, motivo=data.motivo, concepto_dian=data.concepto_dian,
        periodo_id=periodo.id, cliente_id=factura.cliente_id,
        moneda_id=factura.moneda_id, trm=factura.trm,
        descripcion=data.descripcion, estado="borrador",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(dev)
    db.flush()
    subtotal, total_iva, total_ret, total = _persistir_lineas(db, dev, lineas, params)
    dev.subtotal, dev.total_iva, dev.total_retenciones, dev.total = subtotal, total_iva, total_ret, total
    db.commit()
    db.refresh(dev)
    return _to_response(db, dev)


def actualizar(db: Session, id: uuid.UUID, data: DevolucionUpdate, actor: UsuarioActual) -> DevolucionResponse:
    dev = db.query(FacDevolucion).filter(FacDevolucion.id == id, FacDevolucion.activo == True).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    if dev.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se pueden editar devoluciones en borrador")
    factura = _factura_contab(db, dev.factura_id)
    params = db.query(CxcParametroContable).first()

    if data.fecha is not None:
        periodo = _buscar_periodo(db, data.fecha)
        dev.periodo_id = periodo.id
        dev.fecha = data.fecha
    if data.motivo is not None:       dev.motivo = data.motivo
    if data.concepto_dian is not None: dev.concepto_dian = data.concepto_dian
    if data.descripcion is not None:   dev.descripcion = data.descripcion

    if data.lineas is not None:
        lineas = _construir_lineas(db, factura, data.lineas, excluir_dev_id=dev.id)
        db.query(FacDevolucionLinea).filter(FacDevolucionLinea.devolucion_id == dev.id).delete()
        db.flush()
        subtotal, total_iva, total_ret, total = _persistir_lineas(db, dev, lineas, params)
        dev.subtotal, dev.total_iva, dev.total_retenciones, dev.total = subtotal, total_iva, total_ret, total

    dev.modificado_por = uuid.UUID(actor.id)
    dev.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dev)
    return _to_response(db, dev)


def eliminar(db: Session, id: uuid.UUID, actor: UsuarioActual) -> None:
    dev = db.query(FacDevolucion).filter(FacDevolucion.id == id, FacDevolucion.activo == True).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    if dev.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se pueden descartar devoluciones en borrador")
    dev.activo = False
    dev.estado = "anulado"
    dev.modificado_por = uuid.UUID(actor.id)
    dev.modificado_en = datetime.now(timezone.utc)
    db.commit()


# ---------------------------------------------------------------------------
# Asiento (construcción común preview / real)
# ---------------------------------------------------------------------------

def _lineas_asiento_nc(db: Session, dev: FacDevolucion, params, preview: bool):
    """Arma las líneas del asiento de la NC. Retorna (lineas, avisos)."""
    avisos: list[str] = []
    out: list[dict] = []

    def problema(msg: str):
        if preview: avisos.append(msg)
        else: raise HTTPException(status_code=400, detail=msg)

    cliente = db.get(AdmTercero, dev.cliente_id)
    cli_nom = cliente.razon_social if cliente else None

    cuenta_clientes = db.get(CntCuenta, params.cuenta_clientes_id) if params and params.cuenta_clientes_id else None
    if not cuenta_clientes:
        problema("Configura la cuenta de clientes en Administración → Parámetros CxC.")

    def add(cuenta, debito, credito, cc_id=None):
        cc_txt = None
        if cc_id:
            cc = db.get(CntCentroCosto, cc_id)
            cc_txt = f"{cc.codigo} {cc.nombre}" if cc else None
        out.append({
            "cuenta_id": cuenta.id if cuenta else None,
            "cuenta_codigo": cuenta.codigo if cuenta else None,
            "cuenta_nombre": cuenta.nombre if cuenta else "(sin cuenta)",
            "tercero_id": dev.cliente_id, "tercero_nombre": cli_nom,
            "centro_costo_id": cc_id, "centro_costo": cc_txt,
            "debito": debito, "credito": credito,
        })

    for l in sorted(dev.lineas, key=lambda x: x.orden):
        cta_dev = db.get(CntCuenta, l.cuenta_devolucion_id) if l.cuenta_devolucion_id else None
        if not cta_dev:
            problema(f"La línea '{l.descripcion}' no tiene cuenta de devolución. "
                     "Configúrala en el concepto/producto o en Parámetros CxC (cuenta de devolución en ventas).")
        elif cta_dev.requiere_cc and not l.centro_costo_id:
            problema(f"La cuenta '{cta_dev.codigo}' requiere centro de costo en la línea '{l.descripcion}'.")
        add(cta_dev, l.subtotal, Decimal("0"), cc_id=l.centro_costo_id)
        if l.total_iva and l.total_iva > 0:
            cta_iva = db.get(CntCuenta, l.cuenta_iva_id) if l.cuenta_iva_id else None
            if not cta_iva and params and params.cuenta_iva_id:
                cta_iva = db.get(CntCuenta, params.cuenta_iva_id)
            if not cta_iva:
                problema(f"La línea '{l.descripcion}' tiene IVA pero no tiene cuenta IVA.")
            add(cta_iva, l.total_iva, Decimal("0"))

    # Cr Retenciones a favor — reversa el débito que hizo la factura, en la
    # proporción devuelta. Sin esto el saldo de la cuenta queda inflado y no
    # cuadra con el certificado que el cliente emite al cierre.
    for r in dev.retenciones:
        if not r.valor or r.valor <= 0:
            continue
        cta_ret = db.get(CntCuenta, r.cuenta_id) if r.cuenta_id else None
        if not cta_ret:
            problema(f"La retención '{r.concepto}' no tiene cuenta contable.")
            continue
        add(cta_ret, Decimal("0"), r.valor)

    # Cr Clientes por el NETO: `dev.total` ya viene con las retenciones restadas.
    add(cuenta_clientes, Decimal("0"), dev.total)
    return out, avisos


def _persistir_lineas_asiento(db, asiento_id, dev, lineas, moneda_func):
    trm = dev.trm or Decimal("1")
    extranjera = dev.moneda_id != moneda_func.id
    for orden, l in enumerate(lineas, start=1):
        d, c = l["debito"], l["credito"]
        d_f = (d * trm).quantize(Q) if extranjera else d
        c_f = (c * trm).quantize(Q) if extranjera else c
        db.add(CntAsientoLinea(
            id=uuid.uuid4(), asiento_id=asiento_id, orden=orden,
            cuenta_id=l["cuenta_id"], debito=d, credito=c,
            debito_funcional=d_f, credito_funcional=c_f,
            tercero_id=l["tercero_id"], centro_costo_id=l["centro_costo_id"],
        ))


def preview_asiento_nuevo(db: Session, data: DevolucionCreate) -> DevPreviewResponse:
    """Preview del asiento de la NC a partir del payload (sin persistir), para poder
    verlo antes de guardar una devolución nueva."""
    factura = _factura_contab(db, data.factura_id)
    params = db.query(CxcParametroContable).first()
    lineas = _construir_lineas(db, factura, data.lineas)

    dev = FacDevolucion(
        id=uuid.uuid4(), factura_id=factura.id, fecha=data.fecha, motivo=data.motivo or "",
        cliente_id=factura.cliente_id, moneda_id=factura.moneda_id, trm=factura.trm,
    )
    dev.lineas = []
    subtotal = total_iva = Decimal("0")
    for l in lineas:
        cta_dev = _resolver_cuenta_devolucion(db, l["_fl"], params)
        dev.lineas.append(FacDevolucionLinea(
            id=uuid.uuid4(), orden=l["orden"], factura_linea_id=l["factura_linea_id"],
            producto_id=l["producto_id"], descripcion=l["descripcion"], cantidad=l["cantidad"],
            precio_unitario=l["precio_unitario"], subtotal=l["subtotal"], iva_tipo=l["iva_tipo"],
            iva_pct=l["iva_pct"], total_iva=l["total_iva"], total=l["total"],
            cuenta_devolucion_id=cta_dev.id if cta_dev else None,
            cuenta_iva_id=l["cuenta_iva_id"], centro_costo_id=l["centro_costo_id"],
        ))
        subtotal += l["subtotal"]
        total_iva += l["total_iva"]
    dev.subtotal, dev.total_iva, dev.total = subtotal, total_iva, subtotal + total_iva

    lineas_asi, avisos = _lineas_asiento_nc(db, dev, params, preview=True)
    total_d = sum((x["debito"] for x in lineas_asi), Decimal("0"))
    total_c = sum((x["credito"] for x in lineas_asi), Decimal("0"))
    moneda = db.get(AdmMoneda, dev.moneda_id)
    return DevPreviewResponse(
        lineas=[DevPreviewLinea(
            cuenta_codigo=x["cuenta_codigo"], cuenta_nombre=x["cuenta_nombre"],
            tercero_nombre=x["tercero_nombre"], centro_costo=x["centro_costo"],
            debito=x["debito"], credito=x["credito"],
        ) for x in lineas_asi],
        total_debito=total_d, total_credito=total_c,
        cuadra=abs(total_d - total_c) <= Decimal("0.01"),
        moneda_codigo=moneda.codigo if moneda else None, avisos=avisos,
    )


def preview_asiento(db: Session, id: uuid.UUID) -> DevPreviewResponse:
    dev = db.query(FacDevolucion).filter(FacDevolucion.id == id, FacDevolucion.activo == True).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    params = db.query(CxcParametroContable).first()
    lineas, avisos = _lineas_asiento_nc(db, dev, params, preview=True)
    total_d = sum((l["debito"] for l in lineas), Decimal("0"))
    total_c = sum((l["credito"] for l in lineas), Decimal("0"))
    moneda = db.get(AdmMoneda, dev.moneda_id)
    return DevPreviewResponse(
        lineas=[DevPreviewLinea(
            cuenta_codigo=l["cuenta_codigo"], cuenta_nombre=l["cuenta_nombre"],
            tercero_nombre=l["tercero_nombre"], centro_costo=l["centro_costo"],
            debito=l["debito"], credito=l["credito"],
        ) for l in lineas],
        total_debito=total_d, total_credito=total_c,
        cuadra=abs(total_d - total_c) <= Decimal("0.01"),
        moneda_codigo=moneda.codigo if moneda else None, avisos=avisos,
    )


def asiento_contabilizado(db: Session, id: uuid.UUID) -> DevPreviewResponse:
    dev = db.query(FacDevolucion).filter(FacDevolucion.id == id).first()
    if not dev or not dev.asiento_id:
        return DevPreviewResponse(lineas=[], total_debito=Decimal("0"), total_credito=Decimal("0"),
                                  cuadra=True, moneda_codigo=None, avisos=["La devolución aún no está contabilizada."])
    asiento = db.get(CntAsiento, dev.asiento_id)
    lns = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == dev.asiento_id).order_by(CntAsientoLinea.orden).all()
    out = []
    for l in lns:
        c = db.get(CntCuenta, l.cuenta_id) if l.cuenta_id else None
        terc = db.get(AdmTercero, l.tercero_id) if l.tercero_id else None
        cc = db.get(CntCentroCosto, l.centro_costo_id) if l.centro_costo_id else None
        out.append(DevPreviewLinea(
            cuenta_codigo=c.codigo if c else None, cuenta_nombre=c.nombre if c else None,
            tercero_nombre=terc.razon_social if terc else None,
            centro_costo=f"{cc.codigo} {cc.nombre}" if cc else None,
            debito=l.debito, credito=l.credito,
        ))
    total_d = sum((l.debito for l in lns), Decimal("0"))
    total_c = sum((l.credito for l in lns), Decimal("0"))
    moneda = db.get(AdmMoneda, dev.moneda_id)
    return DevPreviewResponse(
        lineas=out, total_debito=total_d, total_credito=total_c,
        cuadra=abs(total_d - total_c) <= Decimal("0.01"),
        moneda_codigo=moneda.codigo if moneda else None, avisos=[],
        asiento_numero=asiento.numero if asiento else None,
    )


# ---------------------------------------------------------------------------
# Inventario: entrada por líneas de producto
# ---------------------------------------------------------------------------

def _entrada_inventario(db: Session, dev: FacDevolucion, factura: FacFactura, actor: UsuarioActual) -> None:
    """Reingresa a inventario los productos devueltos (DEVOLUCION_CLIENTE) al costo
    original de venta, con asiento Dr Inventario / Cr Costo de ventas."""
    from app.services import inventario_service
    lineas_prod = [l for l in dev.lineas if l.producto_id]
    if not lineas_prod:
        return
    if not factura.bodega_id:
        raise HTTPException(status_code=400,
            detail="La factura no tiene bodega asociada; no se puede reingresar el producto devuelto.")

    moneda_func = _moneda_funcional(db)
    td_mov, numero_mov = inventario_service._generar_numero(db, "RM")

    mov = InvMovimiento(
        id=uuid.uuid4(), tipo="DEVOLUCION_CLIENTE",
        fecha=datetime(dev.fecha.year, dev.fecha.month, dev.fecha.day),
        periodo_id=dev.periodo_id, bodega_id=factura.bodega_id,
        numero=numero_mov or f"DEVC-{dev.numero}",
        descripcion=f"Devolución cliente — NC {dev.numero} (factura {factura.numero})",
        estado="borrador", origen_tipo="fac_devolucion", origen_id=dev.id,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(mov)
    db.flush()

    # Asiento del reingreso (Dr Inventario / Cr Costo de ventas)
    asiento = CntAsiento(
        id=uuid.uuid4(), tipo_documento_id=td_mov,
        documento_numero=mov.numero, fecha=dev.fecha, periodo_id=dev.periodo_id,
        descripcion=f"REINGRESO DEVOLUCIÓN {dev.numero} — {factura.numero}",
        estado="borrador", moneda_id=dev.moneda_id,
        trm=dev.trm if dev.moneda_id != moneda_func.id else None,
        documento_origen_id=dev.id, documento_origen_tipo="fac_devolucion_inventario",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(asiento)
    db.flush()

    orden_mov = orden_asi = 0
    for l in lineas_prod:
        prod = db.get(InvProducto, l.producto_id)
        if not prod or not prod.maneja_inventario:
            continue
        fl = next((x for x in factura.lineas if x.id == l.factura_linea_id), None)
        factor = _factor_um(db, prod, fl.um_id if fl else None)
        cantidad_base = (Decimal(str(l.cantidad)) * factor).quantize(Q)

        # Costo original de venta: de la línea de remisión que despachó; si no, costo promedio.
        costo_unit = None
        if fl and fl.remision_linea_id:
            rl = db.get(InvRemisionLinea, fl.remision_linea_id)
            if rl and rl.costo_unitario and rl.costo_unitario > 0:
                costo_unit = Decimal(str(rl.costo_unitario))
        pb = inventario_service._get_or_create_pb(db, prod.id, factura.bodega_id)
        if costo_unit is None:
            costo_unit = Decimal(str(pb.costo_promedio)) if pb.costo_promedio and pb.costo_promedio > 0 else Decimal("0")
        costo_total = (cantidad_base * costo_unit).quantize(Q)

        orden_mov += 1
        db.add(InvMovimientoLinea(
            id=uuid.uuid4(), movimiento_id=mov.id, producto_id=prod.id,
            cantidad=l.cantidad, um_id=fl.um_id if fl else prod.um_base_id,
            cantidad_base=cantidad_base, costo_unitario=costo_unit, costo_total=costo_total,
        ))
        # Reingreso al stock (promedio ponderado)
        stock_ant = Decimal(str(pb.cantidad)); costo_ant = Decimal(str(pb.costo_promedio))
        nueva_cant = stock_ant + cantidad_base
        pb.cantidad = nueva_cant
        pb.costo_promedio = ((stock_ant * costo_ant + costo_total) / nueva_cant).quantize(Q) if nueva_cant > 0 else costo_unit

        if costo_total > 0:
            cta_inv = inventario_service._resolver_cuenta_inventario_inv(db, prod)
            cta_costo = inventario_service._resolver_cuenta_ajuste(db, prod, "cuenta_costo_ventas_id")
            if not cta_inv or not cta_costo:
                raise HTTPException(status_code=400,
                    detail=f"El producto '{prod.nombre}' no tiene cuenta de inventario o de costo de ventas configurada.")
            cf = (costo_total * (dev.trm or Decimal("1"))).quantize(Q) if dev.moneda_id != moneda_func.id else costo_total
            orden_asi += 1
            db.add(CntAsientoLinea(id=uuid.uuid4(), asiento_id=asiento.id, orden=orden_asi,
                cuenta_id=cta_inv.id, debito=costo_total, credito=Decimal("0"),
                debito_funcional=cf, credito_funcional=Decimal("0")))
            orden_asi += 1
            db.add(CntAsientoLinea(id=uuid.uuid4(), asiento_id=asiento.id, orden=orden_asi,
                cuenta_id=cta_costo.id, debito=Decimal("0"), credito=costo_total,
                debito_funcional=Decimal("0"), credito_funcional=cf))

    mov.estado = "confirmado"
    if orden_asi > 0:
        asiento.estado = "publicado"
        mov.asiento_id = asiento.id
    else:
        # Sin costo → no hay asiento de inventario; se descarta el header vacío.
        db.delete(asiento)


# ---------------------------------------------------------------------------
# Contabilizar / anular
# ---------------------------------------------------------------------------

def contabilizar(db: Session, id: uuid.UUID, actor: UsuarioActual) -> DevolucionResponse:
    dev = db.query(FacDevolucion).filter(FacDevolucion.id == id, FacDevolucion.activo == True).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    if dev.estado != "borrador":
        raise HTTPException(status_code=409, detail="La devolución ya está contabilizada o anulada")
    if not dev.lineas:
        raise HTTPException(status_code=400, detail="La devolución no tiene líneas")
    if dev.total <= 0:
        raise HTTPException(status_code=400, detail="El total de la devolución debe ser mayor que cero")

    periodo = db.get(CntPeriodo, dev.periodo_id)
    if not periodo or periodo.estado != "abierto":
        raise HTTPException(status_code=400, detail="El período contable no está abierto")

    factura = _factura_contab(db, dev.factura_id)
    if not factura.cxc_documento_id:
        raise HTTPException(status_code=400, detail="La factura no tiene documento de cartera asociado")

    params = db.query(CxcParametroContable).first()
    moneda_func = _moneda_funcional(db)
    td_nc = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == CODIGO_NC).first()

    # 1. Asiento de la NC
    asiento = CntAsiento(
        id=uuid.uuid4(), tipo_documento_id=td_nc.id if td_nc else None,
        documento_numero=dev.numero, fecha=dev.fecha, periodo_id=dev.periodo_id,
        descripcion=f"NOTA CRÉDITO {dev.numero} — devolución factura {factura.numero}",
        estado="borrador", moneda_id=dev.moneda_id,
        trm=dev.trm if dev.moneda_id != moneda_func.id else None,
        documento_origen_id=dev.id, documento_origen_tipo="fac_devolucion",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(asiento)
    db.flush()
    lineas, _ = _lineas_asiento_nc(db, dev, params, preview=False)
    _persistir_lineas_asiento(db, asiento.id, dev, lineas, moneda_func)
    db.flush()

    filas = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asiento.id).all()
    total_d = sum(f.debito_funcional for f in filas)
    total_c = sum(f.credito_funcional for f in filas)
    if abs(total_d - total_c) > Decimal("0.01"):
        raise HTTPException(status_code=400, detail=f"El asiento no cuadra: D={total_d} C={total_c}")
    asiento.estado = "publicado"

    # 2. Documento CxC NOTA_CREDITO + cruce contra la factura
    cxc_fac = db.get(CxcDocumento, factura.cxc_documento_id)
    cxc_nc = CxcDocumento(
        id=uuid.uuid4(), numero=dev.numero, tipo=TIPO_NC,
        fecha=dev.fecha, periodo_id=dev.periodo_id, tercero_id=dev.cliente_id,
        moneda_id=dev.moneda_id, trm=dev.trm,
        subtotal=dev.subtotal, total_iva=dev.total_iva,
        total_retenciones=dev.total_retenciones,
        total=dev.total, saldo=dev.total,
        descripcion=f"Devolución factura {factura.numero} — {dev.motivo}",
        estado="contabilizado", asiento_id=asiento.id,
        factura_afectada_id=cxc_fac.id if cxc_fac else None,
        origen_modulo="fac_devolucion", origen_id=dev.id,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(cxc_nc)
    db.flush()

    if cxc_fac and cxc_fac.estado == "contabilizado" and cxc_fac.saldo > 0:
        valor = min(cxc_nc.saldo, cxc_fac.saldo)
        if valor > 0:
            db.add(CxcAplicacion(
                id=uuid.uuid4(), documento_credito_id=cxc_nc.id, documento_debito_id=cxc_fac.id,
                valor=valor, fecha=dev.fecha, estado="aplicado", creado_por=uuid.UUID(actor.id),
            ))
            cxc_nc.saldo -= valor
            cxc_fac.saldo -= valor

    # 3. Entrada de inventario (solo líneas de producto)
    _entrada_inventario(db, dev, factura, actor)

    dev.asiento_id = asiento.id
    dev.cxc_documento_id = cxc_nc.id
    dev.estado = "contabilizado"
    dev.dian_estado = "pendiente"
    dev.modificado_por = uuid.UUID(actor.id)
    dev.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(dev)
    return _to_response(db, dev)


def anular(db: Session, id: uuid.UUID, data: AnularDevolucionRequest, actor: UsuarioActual) -> DevolucionResponse:
    dev = db.query(FacDevolucion).filter(FacDevolucion.id == id, FacDevolucion.activo == True).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    if dev.estado == "anulado":
        raise HTTPException(status_code=409, detail="La devolución ya está anulada")
    if dev.estado == "borrador":
        dev.activo = False
        dev.estado = "anulado"
        dev.modificado_por = uuid.UUID(actor.id)
        dev.modificado_en = datetime.now(timezone.utc)
        db.commit()
        db.refresh(dev)
        return _to_response(db, dev)

    periodo = db.get(CntPeriodo, dev.periodo_id)
    if not periodo or periodo.estado != "abierto":
        raise HTTPException(status_code=400, detail="El período contable no está abierto. No se puede anular.")

    moneda_func = _moneda_funcional(db)

    # Reversar la aplicación NC↔factura y devolver el saldo a la factura.
    cxc_nc = db.get(CxcDocumento, dev.cxc_documento_id) if dev.cxc_documento_id else None
    if cxc_nc:
        apps = db.query(CxcAplicacion).filter(
            CxcAplicacion.documento_credito_id == cxc_nc.id, CxcAplicacion.estado == "aplicado",
        ).all()
        for ap in apps:
            fac_doc = db.get(CxcDocumento, ap.documento_debito_id)
            if fac_doc and fac_doc.estado == "contabilizado":
                fac_doc.saldo += ap.valor
            ap.estado = "pendiente"
            db.delete(ap)
        cxc_nc.estado = "anulado"
        cxc_nc.saldo = Decimal("0")

    # Contraasiento de la NC
    def _contra(asiento_id, sufijo, origen_tipo):
        asi = db.get(CntAsiento, asiento_id) if asiento_id else None
        if not asi:
            return
        lns = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == asi.id).all()
        td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "ANU").first()
        contra = CntAsiento(
            id=uuid.uuid4(), tipo_documento_id=td.id if td else None,
            documento_numero=f"ANU-{dev.numero}{sufijo}", fecha=date.today(), periodo_id=dev.periodo_id,
            descripcion=f"ANULACIÓN DEVOLUCIÓN {dev.numero} — {data.motivo}",
            estado="publicado", moneda_id=dev.moneda_id,
            trm=dev.trm if dev.moneda_id != moneda_func.id else None,
            documento_origen_id=dev.id, documento_origen_tipo=origen_tipo,
            creado_por=uuid.UUID(actor.id),
        )
        db.add(contra)
        db.flush()
        for i, l in enumerate(lns, start=1):
            db.add(CntAsientoLinea(
                id=uuid.uuid4(), asiento_id=contra.id, orden=i, cuenta_id=l.cuenta_id,
                debito=l.credito, credito=l.debito,
                debito_funcional=l.credito_funcional, credito_funcional=l.debito_funcional,
                tercero_id=l.tercero_id, centro_costo_id=l.centro_costo_id,
            ))

    _contra(dev.asiento_id, "", "fac_devolucion_anulacion")

    # Reversar la entrada de inventario: salida por las mismas cantidades/costos.
    movs = db.query(InvMovimiento).filter(
        InvMovimiento.origen_tipo == "fac_devolucion", InvMovimiento.origen_id == dev.id,
        InvMovimiento.estado != "anulado",
    ).all()
    from app.services import inventario_service
    for mov in movs:
        mlineas = db.query(InvMovimientoLinea).filter(InvMovimientoLinea.movimiento_id == mov.id).all()
        for ml in mlineas:
            pb = inventario_service._get_or_create_pb(db, ml.producto_id, mov.bodega_id)
            pb.cantidad = Decimal(str(pb.cantidad)) - Decimal(str(ml.cantidad_base))
        _contra(mov.asiento_id, "-INV", "fac_devolucion_inv_anulacion")
        mov.estado = "anulado"
        mov.modificado_por = uuid.UUID(actor.id)
        mov.modificado_en = datetime.now(timezone.utc)

    dev.estado = "anulado"
    dev.activo = False
    dev.modificado_por = uuid.UUID(actor.id)
    dev.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dev)
    return _to_response(db, dev)
