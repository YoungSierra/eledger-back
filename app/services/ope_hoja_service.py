"""Hoja de operaciones — resumen imprimible de toda la carpeta.

Documento INTERNO: lleva costos, proveedores y margen. No se le entrega al
cliente.

La regla de oro del armado es que quepa en dos hojas, así que aquí se RESUME,
no se lista: los costos van agrupados por proveedor (no concepto por concepto) y
la bitácora se corta en los últimos eventos. El detalle línea por línea ya lo da
la impresión de la cotización.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.adm import AdmTercero
from app.models.facturacion import FacFactura
from app.models.ope import (
    OpeAerolinea, OpeAeropuerto, OpeConfirmacionLinea, OpeEvento, OpeHawb,
    OpeManifiesto, OpeMawb, OpeOperacion,
)
from app.schemas.ope import (
    HojaCotizacion, HojaEvento, HojaFactura, HojaGuia, HojaManifiesto,
    HojaProveedor, OpeHojaResponse,
)

MAX_EVENTOS = 8
CERO = Decimal("0")


def _a_cop(valor, moneda: str, trm) -> Decimal:
    """Lleva un valor a pesos. Sin TRM, un USD no se puede convertir: se deja
    como está y el número queda visiblemente bajo, no inventado."""
    v = Decimal(str(valor or 0))
    if moneda != "USD":
        return v
    t = Decimal(str(trm or 0))
    return v * t if t > 0 else v


def _nombre_tercero(db: Session, tid) -> str:
    if not tid:
        return ""
    t = db.get(AdmTercero, tid)
    return t.razon_social if t else ""


def generar_hoja(db: Session, operacion_id: uuid.UUID) -> OpeHojaResponse:
    from app.services import facturacion_service

    op = db.query(OpeOperacion).filter(
        OpeOperacion.id == operacion_id, OpeOperacion.activo == True
    ).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operación no encontrada")

    cots = [c for c in op.cotizaciones if c.activo]
    cots.sort(key=lambda c: c.numero)

    confirmadas = {
        f.cotizacion_linea_id: f
        for f in db.query(OpeConfirmacionLinea).filter(
            OpeConfirmacionLinea.operacion_id == op.id,
            OpeConfirmacionLinea.activo == True,
        ).all()
    }

    # ── Económico por cotización ───────────────────────────────────────────
    filas_cot: list[HojaCotizacion] = []
    t_cot = t_conf = t_fact = t_pend = CERO
    # Costos acumulados por proveedor
    prov: dict[str, dict] = {}
    t_costo_cot = t_costo_conf = CERO

    for c in cots:
        trm = c.trm
        cot_cop = conf_cop = CERO
        confirmadas_n = opcionales_n = 0

        for l in c.lineas:
            cf = confirmadas.get(l.id)
            esta_confirmada = bool(cf and cf.confirmado)
            if esta_confirmada:
                confirmadas_n += 1
            if l.opcional:
                opcionales_n += 1

            # Lo cotizado: los opcionales no suman, igual que en la cotización.
            if not l.opcional:
                cot_cop += _a_cop(l.total_venta, l.moneda, trm)
            # Lo confirmado: solo lo que operaciones marcó, opcional o no.
            if esta_confirmada:
                conf_cop += _a_cop(cf.total_venta_confirmado, l.moneda, trm)

            # Costos por proveedor
            nombre = _nombre_tercero(db, l.proveedor_id) or "Sin proveedor asignado"
            p = prov.setdefault(nombre, {"conceptos": 0, "cot": CERO, "conf": CERO})
            p["conceptos"] += 1
            if not l.opcional:
                p["cot"] += _a_cop(l.total_costo, l.moneda, trm)
            if esta_confirmada:
                p["conf"] += _a_cop(cf.total_costo_confirmado, l.moneda, trm)

        est = facturacion_service.estado_facturacion_cotizacion(db, c.id)
        fact_cop = sum(
            (_a_cop(x["facturado"], x["moneda"], trm) for x in est["lineas"]), CERO
        )
        pend_cop = conf_cop - fact_cop

        filas_cot.append(HojaCotizacion(
            numero=c.numero,
            cliente_nombre=_nombre_tercero(db, c.cliente_id),
            moneda=c.moneda_mercancia,
            trm=trm,
            cotizado_cop=cot_cop,
            confirmado_cop=conf_cop,
            facturado_cop=fact_cop,
            pendiente_cop=pend_cop if pend_cop > 0 else CERO,
            estado_facturacion=est["estado_facturacion"],
            lineas_total=len(c.lineas),
            lineas_confirmadas=confirmadas_n,
            opcionales=opcionales_n,
        ))
        t_cot += cot_cop
        t_conf += conf_cop
        t_fact += fact_cop
        t_pend += pend_cop if pend_cop > 0 else CERO

    proveedores = [
        HojaProveedor(
            proveedor=nombre,
            conceptos=d["conceptos"],
            costo_cotizado_cop=d["cot"],
            costo_confirmado_cop=d["conf"],
        )
        for nombre, d in sorted(prov.items(), key=lambda kv: -kv[1]["cot"])
    ]
    for p in proveedores:
        t_costo_cot += p.costo_cotizado_cop
        t_costo_conf += p.costo_confirmado_cop

    # El margen se mide sobre lo confirmado: es lo que de verdad se va a facturar.
    margen = t_conf - t_costo_conf
    margen_pct = (margen / t_conf * 100) if t_conf > 0 else CERO

    # ── Facturas ───────────────────────────────────────────────────────────
    facturas: list[HojaFactura] = []
    if cots:
        cot_por_id = {c.id: c for c in cots}
        for f in db.query(FacFactura).filter(
            FacFactura.cotizacion_id.in_([c.id for c in cots]),
            FacFactura.activo == True,
        ).order_by(FacFactura.fecha, FacFactura.numero).all():
            c = cot_por_id.get(f.cotizacion_id)
            cod = getattr(f, "moneda_codigo", None) or "COP"
            facturas.append(HojaFactura(
                numero=f.numero,
                fecha=f.fecha,
                cliente_nombre=_nombre_tercero(db, f.cliente_id),
                moneda=cod,
                total=Decimal(str(f.total or 0)),
                total_cop=_a_cop(f.total, cod, f.trm or (c.trm if c else None)),
                estado=f.estado,
                dian_estado=f.dian_estado,
            ))

    # ── Operativo ──────────────────────────────────────────────────────────
    def aerolinea_nombre(aid):
        a = db.get(OpeAerolinea, aid) if aid else None
        return a.codigo_iata if a else None

    mawbs = [
        HojaGuia(
            numero=f"{m.prefix or ''}{m.numero_mawb}",
            referencia=aerolinea_nombre(m.aerolinea_id),
            vuelo=m.vuelo, fecha_vuelo=m.fecha_vuelo,
            piezas=m.piezas, peso_kg=m.peso_bruto_kg, estado=m.estado,
        )
        for m in sorted(op.mawbs, key=lambda x: x.numero_mawb)
    ]

    cot_numeros = {c.id: c.numero for c in cots}
    hawbs = [
        HojaGuia(
            numero=h.numero_hawb,
            referencia=_nombre_tercero(db, h.consignee_id) or cot_numeros.get(h.cotizacion_id),
            vuelo=h.vuelo, fecha_vuelo=h.fecha_vuelo,
            piezas=h.piezas, peso_kg=h.peso_bruto_kg, estado=h.estado,
        )
        for h in sorted(op.hawbs, key=lambda x: x.numero_hawb)
    ]

    manifiestos = []
    for mf in sorted(op.manifiestos, key=lambda x: x.fecha):
        mw = db.get(OpeMawb, mf.mawb_id) if mf.mawb_id else None
        manifiestos.append(HojaManifiesto(
            fecha=mf.fecha,
            mawb=f"{mw.prefix or ''}{mw.numero_mawb}" if mw else None,
            aerolinea=aerolinea_nombre(mf.aerolinea_id),
            hawbs=len(mf.lineas),
            piezas=sum((l.piezas or 0) for l in mf.lineas) or None,
            peso_kg=sum((Decimal(str(l.peso_kg or 0)) for l in mf.lineas), CERO) or None,
            estado=mf.estado,
        ))

    # ── Bitácora: solo los últimos, con el total para saber que hay más ────
    q_ev = db.query(OpeEvento).filter(OpeEvento.operacion_id == op.id)
    eventos_total = q_ev.count()
    hawb_num = {h.id: h.numero_hawb for h in op.hawbs}
    eventos = [
        HojaEvento(
            fecha_hora=e.fecha_hora, tipo=e.tipo, descripcion=e.descripcion,
            hawb_numero=hawb_num.get(e.hawb_id),
        )
        for e in q_ev.order_by(OpeEvento.fecha_hora.desc()).limit(MAX_EVENTOS).all()
    ]

    # ── Encabezado ─────────────────────────────────────────────────────────
    ruta = None
    if cots:
        ruta = f"{cots[0].origen} → {cots[0].destino}"
    piezas = [c.piezas for c in cots if c.piezas is not None]
    pesos = [c.peso_kg for c in cots if c.peso_kg is not None]

    return OpeHojaResponse(
        numero=op.numero,
        estado=op.estado,
        fecha_apertura=op.fecha_apertura,
        aerolinea=aerolinea_nombre(op.aerolinea_id),
        ruta=ruta,
        piezas_total=sum(piezas) if piezas else op.piezas,
        peso_kg_total=sum(pesos) if pesos else op.peso_kg,
        clientes=list(dict.fromkeys(f.cliente_nombre for f in filas_cot if f.cliente_nombre)),
        cotizaciones=filas_cot,
        total_cotizado_cop=t_cot,
        total_confirmado_cop=t_conf,
        total_facturado_cop=t_fact,
        total_pendiente_cop=t_pend,
        facturas=facturas,
        proveedores=proveedores,
        total_costo_cotizado_cop=t_costo_cot,
        total_costo_confirmado_cop=t_costo_conf,
        margen_cop=margen,
        margen_pct=margen_pct,
        mawbs=mawbs,
        hawbs=hawbs,
        manifiestos=manifiestos,
        eventos=eventos,
        eventos_total=eventos_total,
        generado_en=datetime.now(timezone.utc),
    )
