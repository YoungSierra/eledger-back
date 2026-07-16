import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING

from fastapi import HTTPException, status
from sqlalchemy import cast, Date, func
from sqlalchemy.orm import Session, joinedload

from app.models.adm import AdmTercero
from app.models.admin import AdmMoneda, AdmTrm, AdmUsuario
from app.core.auditoria import registrar as audit
from app.models.ope import OpeCotizacion, OpeCotizacionLinea, OpeOperacion
from app.schemas.auth import UsuarioActual
from app.schemas.ope import (
    OpeCotizacionCreate, OpeCotizacionUpdate,
    OpeCotizacionLineaCreate, OpeCotizacionLineaUpdate,
    OpeCotizacionMargenResponse, LineaMargenResponse, SeccionMargenResponse,
)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _resolver_asesor(
    db: Session,
    cliente_id: uuid.UUID,
    asesor_id_explicito: uuid.UUID | None,
    fallback: uuid.UUID,
) -> uuid.UUID:
    if asesor_id_explicito:
        return asesor_id_explicito
    tercero = db.get(AdmTercero, cliente_id)
    if tercero and tercero.asesor_id:
        return tercero.asesor_id
    return fallback


def _asesor_nombre(db: Session, asesor_id: uuid.UUID | None) -> str | None:
    if not asesor_id:
        return None
    u = db.get(AdmUsuario, asesor_id)
    return f"{u.nombre} {u.apellido}" if u else None

def _generar_numero_cotizacion(db: Session, fecha: date) -> str:
    prefijo = f"COT-{fecha.year}"
    ultimo = (
        db.query(OpeCotizacion)
        .filter(OpeCotizacion.numero.like(f"{prefijo}%"))
        .order_by(OpeCotizacion.numero.desc())
        .first()
    )
    consecutivo = int(ultimo.numero[-4:]) + 1 if ultimo else 1
    return f"{prefijo}{consecutivo:04d}"


def _generar_numero_operacion(db: Session, fecha: date) -> str:
    prefijo = f"OP-{fecha.year}"
    ultimo = (
        db.query(OpeOperacion)
        .filter(OpeOperacion.numero.like(f"{prefijo}%"))
        .order_by(OpeOperacion.numero.desc())
        .first()
    )
    consecutivo = int(ultimo.numero[-4:]) + 1 if ultimo else 1
    return f"{prefijo}{consecutivo:04d}"


def _buscar_trm(db: Session, fecha: date) -> Decimal | None:
    usd = db.query(AdmMoneda).filter(AdmMoneda.codigo == "USD").first()
    cop = db.query(AdmMoneda).filter(AdmMoneda.codigo == "COP").first()
    if not usd or not cop:
        return None
    trm = (
        db.query(AdmTrm)
        .filter(
            AdmTrm.moneda_origen_id == usd.id,
            AdmTrm.moneda_destino_id == cop.id,
            cast(AdmTrm.fecha, Date) == fecha,
        )
        .first()
    )
    return Decimal(str(trm.tasa)) if trm else None


def _calcular_totales_linea(
    tipo_calculo: str,
    valor_unitario: Decimal,
    costo_unitario: Decimal,
    base: Decimal,
    minimo: Decimal | None,
    valor_cif: Decimal | None,
    moneda_cif: str,
    moneda_linea: str,
    trm: Decimal | None,
) -> tuple[Decimal, Decimal]:
    if tipo_calculo == "PORCENTAJE":
        vm = valor_cif or Decimal("0")
        if moneda_cif != moneda_linea and trm:
            vm = vm * trm if moneda_cif == "USD" else vm / trm
        total_v = (valor_unitario / Decimal("100")) * vm
        total_c = (costo_unitario / Decimal("100")) * vm
    else:
        total_v = valor_unitario * base
        total_c = costo_unitario * base

    if minimo is not None:
        total_v = max(total_v, minimo)
        # El mínimo es una condición comercial — solo aplica a la venta, no al costo

    # Porcentajes sobre CIF se elevan al peso entero superior (práctica aduanera Colombia)
    if tipo_calculo == "PORCENTAJE":
        return total_v.quantize(Decimal("1"), ROUND_CEILING), total_c.quantize(Decimal("1"), ROUND_CEILING)

    escala = Decimal("0.0001")
    return total_v.quantize(escala, ROUND_HALF_UP), total_c.quantize(escala, ROUND_HALF_UP)


def _verificar_editable(cotizacion: OpeCotizacion) -> None:
    if cotizacion.estado != "BORRADOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se puede modificar una cotización en BORRADOR. Estado actual: {cotizacion.estado}",
        )


def _marcar_vencidas(db: Session) -> None:
    hoy = date.today()
    db.query(OpeCotizacion).filter(
        OpeCotizacion.estado.in_(["BORRADOR", "ENVIADA"]),
        OpeCotizacion.fecha_vigencia < hoy,
        OpeCotizacion.activo == True,
    ).update({"estado": "VENCIDA"}, synchronize_session=False)
    db.commit()


# ---------------------------------------------------------------------------
# Cotización — CRUD
# ---------------------------------------------------------------------------

def listar_cotizaciones(
    db: Session,
    actor: UsuarioActual,
    estado: str | None = None,
    cliente_id: uuid.UUID | None = None,
    busqueda: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> list[dict]:
    _marcar_vencidas(db)
    q = (
        db.query(OpeCotizacion)
        .options(joinedload(OpeCotizacion.cliente))
        .filter(OpeCotizacion.activo == True)
    )
    if actor.ver_solo_propios:
        q = q.filter(OpeCotizacion.asesor_id == uuid.UUID(actor.id))
    if estado:
        q = q.filter(OpeCotizacion.estado == estado)
    if cliente_id:
        q = q.filter(OpeCotizacion.cliente_id == cliente_id)
    if busqueda:
        term = f"%{busqueda}%"
        q = q.join(AdmTercero, OpeCotizacion.cliente_id == AdmTercero.id).filter(
            OpeCotizacion.numero.ilike(term) |
            OpeCotizacion.origen.ilike(term) |
            OpeCotizacion.destino.ilike(term) |
            AdmTercero.razon_social.ilike(term) |
            AdmTercero.nit.ilike(term)
        )
    if fecha_desde:
        q = q.filter(OpeCotizacion.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(OpeCotizacion.fecha <= fecha_hasta)
    rows = q.order_by(OpeCotizacion.fecha.desc(), OpeCotizacion.creado_en.desc()).all()
    for row in rows:
        row.cliente_nombre = row.cliente.razon_social if row.cliente else ""
        row.asesor_nombre = _asesor_nombre(db, row.asesor_id)
    return rows


def obtener_cotizacion(db: Session, cotizacion_id: uuid.UUID) -> OpeCotizacion:
    _marcar_vencidas(db)
    c = db.query(OpeCotizacion).filter(
        OpeCotizacion.id == cotizacion_id,
        OpeCotizacion.activo == True,
    ).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cotización no encontrada")
    c.asesor_nombre = _asesor_nombre(db, c.asesor_id)
    return c


def crear_cotizacion(db: Session, data: OpeCotizacionCreate, actor: UsuarioActual) -> OpeCotizacion:
    actor_id = uuid.UUID(actor.id)

    trm = data.trm
    trm_advertencia = None
    if trm is None:
        trm = _buscar_trm(db, data.fecha)
        if trm is None:
            trm_advertencia = f"No hay TRM registrada para {data.fecha}. La cotización se creó sin TRM."

    numero = _generar_numero_cotizacion(db, data.fecha)

    cotizacion = OpeCotizacion(
        numero=numero,
        cliente_id=data.cliente_id,
        fecha=data.fecha,
        fecha_vigencia=data.fecha_vigencia,
        tipo_operacion=data.tipo_operacion,
        modalidad=data.modalidad,
        origen=data.origen,
        destino=data.destino,
        aerolinea_id=data.aerolinea_id,
        incoterm=data.incoterm,
        piezas=data.piezas,
        peso_kg=data.peso_kg,
        valor_mercancia=data.valor_mercancia,
        moneda_mercancia=data.moneda_mercancia,
        valor_cif=data.valor_cif,
        trm=trm,
        notas=data.notas,
        asesor_id=_resolver_asesor(db, data.cliente_id, data.asesor_id, actor_id),
        estado="BORRADOR",
        creado_por=actor_id,
    )
    db.add(cotizacion)
    db.flush()  # obtener id sin commit

    for linea_data in data.lineas:
        _agregar_linea(db, cotizacion, linea_data)

    audit(db, "ope_cotizacion", cotizacion.id, "INSERT", actor_id,
          contexto={"numero": cotizacion.numero, "cliente_id": str(cotizacion.cliente_id)})

    db.commit()
    db.refresh(cotizacion)

    if trm_advertencia:
        cotizacion._trm_advertencia = trm_advertencia  # señal al router

    return cotizacion


def actualizar_cotizacion(
    db: Session, cotizacion_id: uuid.UUID, data: OpeCotizacionUpdate, actor: UsuarioActual
) -> OpeCotizacion:
    c = obtener_cotizacion(db, cotizacion_id)
    _verificar_editable(c)

    # Actualizar campos del encabezado (excluir lineas — se manejan aparte)
    for campo, valor in data.model_dump(exclude_none=True, exclude={"lineas"}).items():
        setattr(c, campo, valor)

    actor_id = uuid.UUID(actor.id)
    c.modificado_por = actor_id
    c.modificado_en = datetime.now(timezone.utc)
    audit(db, "ope_cotizacion", c.id, "UPDATE", actor_id,
          contexto={"numero": c.numero, "campos": list(data.model_dump(exclude_none=True, exclude={"lineas"}).keys())})

    if data.lineas is not None:
        # Reemplazo completo: borrar las existentes e insertar las del payload
        for linea in list(c.lineas):
            db.delete(linea)
        db.flush()
        for linea_data in data.lineas:
            _agregar_linea(db, c, linea_data)
    elif data.valor_mercancia is not None or data.trm is not None:
        # Solo recalcular totales si cambiaron los valores de referencia
        for linea in c.lineas:
            tv, tc = _calcular_totales_linea(
                linea.tipo_calculo, linea.valor_unitario, linea.costo_unitario,
                linea.base, linea.minimo, c.valor_cif or c.valor_mercancia, c.moneda_mercancia,
                linea.moneda, c.trm,
            )
            linea.total_venta = tv
            linea.total_costo = tc

    db.commit()
    db.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Líneas
# ---------------------------------------------------------------------------

def _agregar_linea(db: Session, cotizacion: OpeCotizacion, data: OpeCotizacionLineaCreate) -> OpeCotizacionLinea:
    tv, tc = _calcular_totales_linea(
        data.tipo_calculo, data.valor_unitario, data.costo_unitario,
        data.base, data.minimo, cotizacion.valor_cif or cotizacion.valor_mercancia,
        cotizacion.moneda_mercancia, data.moneda, cotizacion.trm,
    )
    linea = OpeCotizacionLinea(
        cotizacion_id=cotizacion.id,
        seccion=data.seccion,
        orden=data.orden,
        concepto_id=data.concepto_id,
        descripcion=data.descripcion,
        tipo_calculo=data.tipo_calculo,
        valor_unitario=data.valor_unitario,
        costo_unitario=data.costo_unitario,
        base=data.base,
        minimo=data.minimo,
        total_venta=tv,
        total_costo=tc,
        moneda=data.moneda,
        proveedor_id=data.proveedor_id,
        condiciones_costo=data.condiciones_costo,
        notas=data.notas,
    )
    db.add(linea)
    return linea


def agregar_linea(
    db: Session, cotizacion_id: uuid.UUID, data: OpeCotizacionLineaCreate, actor: UsuarioActual
) -> OpeCotizacionLinea:
    c = obtener_cotizacion(db, cotizacion_id)
    _verificar_editable(c)
    linea = _agregar_linea(db, c, data)
    db.flush()
    actor_id = uuid.UUID(actor.id)
    audit(db, "ope_cotizacion_linea", linea.id, "INSERT", actor_id,
          contexto={"cotizacion": c.numero, "seccion": data.seccion, "descripcion": data.descripcion})
    db.commit()
    db.refresh(linea)
    return linea


def actualizar_linea(
    db: Session, cotizacion_id: uuid.UUID, linea_id: uuid.UUID,
    data: OpeCotizacionLineaUpdate, actor: UsuarioActual,
) -> OpeCotizacionLinea:
    c = obtener_cotizacion(db, cotizacion_id)
    _verificar_editable(c)
    linea = db.query(OpeCotizacionLinea).filter(
        OpeCotizacionLinea.id == linea_id,
        OpeCotizacionLinea.cotizacion_id == cotizacion_id,
    ).first()
    if not linea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Línea no encontrada")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(linea, campo, valor)

    tv, tc = _calcular_totales_linea(
        linea.tipo_calculo, linea.valor_unitario, linea.costo_unitario,
        linea.base, linea.minimo, c.valor_cif or c.valor_mercancia, c.moneda_mercancia,
        linea.moneda, c.trm,
    )
    linea.total_venta = tv
    linea.total_costo = tc

    actor_id = uuid.UUID(actor.id)
    audit(db, "ope_cotizacion_linea", linea.id, "UPDATE", actor_id,
          contexto={"cotizacion": c.numero, "seccion": linea.seccion,
                    "descripcion": linea.descripcion, "campos": list(data.model_dump(exclude_none=True).keys())})

    db.commit()
    db.refresh(linea)
    return linea


def eliminar_linea(
    db: Session, cotizacion_id: uuid.UUID, linea_id: uuid.UUID, actor: UsuarioActual
) -> None:
    c = obtener_cotizacion(db, cotizacion_id)
    _verificar_editable(c)
    linea = db.query(OpeCotizacionLinea).filter(
        OpeCotizacionLinea.id == linea_id,
        OpeCotizacionLinea.cotizacion_id == cotizacion_id,
    ).first()
    if not linea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Línea no encontrada")
    actor_id = uuid.UUID(actor.id)
    audit(db, "ope_cotizacion_linea", linea.id, "DELETE", actor_id,
          contexto={"cotizacion": c.numero, "seccion": linea.seccion, "descripcion": linea.descripcion})
    db.delete(linea)
    db.commit()


# ---------------------------------------------------------------------------
# Transiciones de estado
# ---------------------------------------------------------------------------

def enviar_cotizacion(db: Session, cotizacion_id: uuid.UUID, actor: UsuarioActual) -> OpeCotizacion:
    c = obtener_cotizacion(db, cotizacion_id)
    if c.estado != "BORRADOR":
        raise HTTPException(status_code=400, detail=f"Solo se puede enviar una cotización en BORRADOR. Estado: {c.estado}")
    if not c.lineas:
        raise HTTPException(status_code=400, detail="No se puede enviar una cotización sin líneas")
    actor_id = uuid.UUID(actor.id)
    c.estado = "ENVIADA"
    c.modificado_por = actor_id
    c.modificado_en = datetime.now(timezone.utc)
    audit(db, "ope_cotizacion", c.id, "UPDATE", actor_id,
          campo="estado", valor_anterior="BORRADOR", valor_nuevo="ENVIADA",
          contexto={"numero": c.numero})
    db.commit()
    db.refresh(c)
    return c


def aprobar_cotizacion(db: Session, cotizacion_id: uuid.UUID, actor: UsuarioActual) -> OpeOperacion:
    c = obtener_cotizacion(db, cotizacion_id)
    if c.estado != "ENVIADA":
        raise HTTPException(status_code=400, detail=f"Solo se puede aprobar una cotización ENVIADA. Estado: {c.estado}")
    actor_id = uuid.UUID(actor.id)
    c.estado = "APROBADA"
    c.modificado_por = actor_id
    c.modificado_en = datetime.now(timezone.utc)

    hoy = date.today()
    operacion = OpeOperacion(
        numero=_generar_numero_operacion(db, hoy),
        cotizacion_id=c.id,
        fecha_apertura=hoy,
        estado="ABIERTA",
        aerolinea_id=c.aerolinea_id,
        piezas=c.piezas,
        peso_kg=c.peso_kg,
        creado_por=actor_id,
    )
    db.add(operacion)
    audit(db, "ope_cotizacion", c.id, "UPDATE", actor_id,
          campo="estado", valor_anterior="ENVIADA", valor_nuevo="APROBADA",
          contexto={"numero": c.numero})
    db.commit()
    db.refresh(operacion)
    return operacion


def reabrir_cotizacion(db: Session, cotizacion_id: uuid.UUID, actor: UsuarioActual) -> OpeCotizacion:
    c = obtener_cotizacion(db, cotizacion_id)
    if c.estado not in ("ENVIADA", "RECHAZADA"):
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede reabrir una cotización ENVIADA o RECHAZADA. Estado actual: {c.estado}",
        )
    actor_id = uuid.UUID(actor.id)
    estado_anterior = c.estado
    c.estado = "BORRADOR"
    c.modificado_por = actor_id
    c.modificado_en = datetime.now(timezone.utc)
    audit(db, "ope_cotizacion", c.id, "UPDATE", actor_id,
          campo="estado", valor_anterior=estado_anterior, valor_nuevo="BORRADOR",
          contexto={"numero": c.numero, "motivo": "reapertura para ajuste"})
    db.commit()
    db.refresh(c)
    return c


def rechazar_cotizacion(db: Session, cotizacion_id: uuid.UUID, actor: UsuarioActual) -> OpeCotizacion:
    c = obtener_cotizacion(db, cotizacion_id)
    if c.estado != "ENVIADA":
        raise HTTPException(status_code=400, detail=f"Solo se puede rechazar una cotización ENVIADA. Estado: {c.estado}")
    actor_id = uuid.UUID(actor.id)
    c.estado = "RECHAZADA"
    c.modificado_por = actor_id
    c.modificado_en = datetime.now(timezone.utc)
    audit(db, "ope_cotizacion", c.id, "UPDATE", actor_id,
          campo="estado", valor_anterior="ENVIADA", valor_nuevo="RECHAZADA",
          contexto={"numero": c.numero})
    db.commit()
    db.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Margen
# ---------------------------------------------------------------------------

def calcular_margen(db: Session, cotizacion_id: uuid.UUID) -> OpeCotizacionMargenResponse:
    c = obtener_cotizacion(db, cotizacion_id)
    trm = c.trm or Decimal("1")

    lineas_resp: list[LineaMargenResponse] = []
    secciones: dict[str, dict] = {}

    for linea in c.lineas:
        margen = linea.total_venta - linea.total_costo
        lineas_resp.append(LineaMargenResponse(
            seccion=linea.seccion,
            descripcion=linea.descripcion,
            moneda=linea.moneda,
            total_venta=linea.total_venta,
            total_costo=linea.total_costo,
            margen=margen,
        ))
        factor = trm if linea.moneda == "USD" else Decimal("1")
        if linea.seccion not in secciones:
            secciones[linea.seccion] = {"venta": Decimal("0"), "costo": Decimal("0")}
        secciones[linea.seccion]["venta"] += linea.total_venta * factor
        secciones[linea.seccion]["costo"] += linea.total_costo * factor

    secciones_resp = [
        SeccionMargenResponse(
            seccion=sec,
            total_venta_cop=vals["venta"].quantize(Decimal("0.01"), ROUND_HALF_UP),
            total_costo_cop=vals["costo"].quantize(Decimal("0.01"), ROUND_HALF_UP),
            margen_cop=(vals["venta"] - vals["costo"]).quantize(Decimal("0.01"), ROUND_HALF_UP),
        )
        for sec, vals in secciones.items()
    ]

    total_venta = sum(s.total_venta_cop for s in secciones_resp)
    total_costo = sum(s.total_costo_cop for s in secciones_resp)
    margen_cop = total_venta - total_costo
    margen_pct = (margen_cop / total_venta * 100).quantize(Decimal("0.01"), ROUND_HALF_UP) if total_venta else Decimal("0")

    return OpeCotizacionMargenResponse(
        cotizacion_id=c.id,
        numero=c.numero,
        trm=trm,
        lineas=lineas_resp,
        secciones=secciones_resp,
        total_venta_cop=total_venta,
        total_costo_cop=total_costo,
        margen_cop=margen_cop,
        margen_pct=margen_pct,
    )
