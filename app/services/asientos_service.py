import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.admin import AdmConsecutivo, AdmMoneda, AdmTipoDocumento, AdmConfiguracion
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntAsientoCorreccion, CntCuenta, CntCentroCosto, CntPeriodo
from app.models.adm import AdmTercero
from app.schemas.asientos import (
    AsientoCreate, AsientoUpdate, AsientoCorregirRequest,
    AsientoResponse, AsientoListItem, AsientoListResponse,
    LineaCreate, LineaUpdate, LineaResponse,
)
from app.schemas.auth import UsuarioActual


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _generar_documento_numero(db: Session, tipo_documento_id: uuid.UUID) -> str:
    """Genera y consume el siguiente número del consecutivo. Atómico con SELECT FOR UPDATE."""
    cons = (
        db.query(AdmConsecutivo)
        .filter(AdmConsecutivo.tipo_documento_id == tipo_documento_id)
        .with_for_update()
        .first()
    )
    if not cons:
        raise HTTPException(status_code=400, detail="No hay consecutivo configurado para este tipo de documento")
    siguiente = max(cons.numero_actual + 1, cons.numero_inicio)
    num = str(siguiente).zfill(cons.longitud_minima)
    resultado = f"{cons.prefijo or ''}{num}"
    cons.numero_actual = siguiente
    return resultado


def _buscar_periodo(db: Session, fecha) -> CntPeriodo:
    periodo = (
        db.query(CntPeriodo)
        .filter(CntPeriodo.fecha_inicio <= fecha, CntPeriodo.fecha_cierre >= fecha, CntPeriodo.activo == True)
        .first()
    )
    if not periodo:
        raise HTTPException(status_code=400, detail=f"No existe período contable para la fecha {fecha}")
    return periodo


def _moneda_funcional(db: Session) -> AdmMoneda:
    m = db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.activo == True).first()
    if not m:
        raise HTTPException(status_code=400, detail="No hay moneda funcional configurada")
    return m


def _calcular_funcional(monto: Decimal, moneda_id: uuid.UUID, moneda_func_id: uuid.UUID, trm: Decimal | None) -> Decimal:
    if moneda_id == moneda_func_id:
        return monto
    if not trm:
        raise HTTPException(status_code=400, detail="Se requiere TRM para moneda extranjera")
    return (monto * trm).quantize(Decimal("0.0001"))


def _enriquecer_linea(linea: CntAsientoLinea, db: Session) -> LineaResponse:
    cuenta = db.get(CntCuenta, linea.cuenta_id)
    tercero = db.get(AdmTercero, linea.tercero_id) if linea.tercero_id else None
    cc = db.get(CntCentroCosto, linea.centro_costo_id) if linea.centro_costo_id else None
    return LineaResponse(
        id=linea.id,
        asiento_id=linea.asiento_id,
        orden=linea.orden,
        cuenta_id=linea.cuenta_id,
        cuenta_codigo=cuenta.codigo if cuenta else "",
        cuenta_nombre=cuenta.nombre if cuenta else "",
        debito=linea.debito,
        credito=linea.credito,
        debito_funcional=linea.debito_funcional,
        credito_funcional=linea.credito_funcional,
        tercero_id=linea.tercero_id,
        tercero_nit=tercero.nit if tercero else None,
        tercero_nombre=tercero.razon_social if tercero else None,
        centro_costo_id=linea.centro_costo_id,
        centro_costo_nombre=cc.nombre if cc else None,
        descripcion=linea.descripcion,
        requiere_tercero=cuenta.requiere_tercero if cuenta else False,
        requiere_cc=cuenta.requiere_cc if cuenta else False,
    )


def _to_response(asiento: CntAsiento, db: Session) -> AsientoResponse:
    td = db.get(AdmTipoDocumento, asiento.tipo_documento_id)
    moneda = db.get(AdmMoneda, asiento.moneda_id)
    lineas_activas = [l for l in asiento.lineas if l.activo]
    total_d = sum(l.debito for l in lineas_activas)
    total_c = sum(l.credito for l in lineas_activas)
    return AsientoResponse(
        id=asiento.id,
        numero=asiento.numero,
        documento_numero=asiento.documento_numero,
        tipo_documento_id=asiento.tipo_documento_id,
        tipo_documento_codigo=td.codigo if td else "",
        tipo_documento_nombre=td.nombre if td else "",
        fecha=asiento.fecha,
        periodo_id=asiento.periodo_id,
        descripcion=asiento.descripcion,
        documento_origen_id=asiento.documento_origen_id,
        documento_origen_tipo=asiento.documento_origen_tipo,
        estado=asiento.estado,
        moneda_id=asiento.moneda_id,
        moneda_codigo=moneda.codigo if moneda else "",
        trm=asiento.trm,
        asiento_origen_id=asiento.asiento_origen_id,
        total_debito=total_d,
        total_credito=total_c,
        lineas=[_enriquecer_linea(l, db) for l in sorted(lineas_activas, key=lambda x: x.orden)],
        creado_en=asiento.creado_en,
        creado_por=asiento.creado_por,
    )


def _to_list_item(asiento: CntAsiento, db: Session) -> AsientoListItem:
    td = db.get(AdmTipoDocumento, asiento.tipo_documento_id)
    moneda = db.get(AdmMoneda, asiento.moneda_id)
    lineas_activas = [l for l in asiento.lineas if l.activo]
    return AsientoListItem(
        id=asiento.id,
        numero=asiento.numero,
        documento_numero=asiento.documento_numero,
        tipo_documento_codigo=td.codigo if td else "",
        tipo_documento_nombre=td.nombre if td else "",
        fecha=asiento.fecha,
        descripcion=asiento.descripcion,
        estado=asiento.estado,
        moneda_codigo=moneda.codigo if moneda else "",
        total_debito=sum(l.debito for l in lineas_activas),
        total_credito=sum(l.credito for l in lineas_activas),
        documento_origen_id=asiento.documento_origen_id,
        creado_en=asiento.creado_en,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def listar(
    db: Session,
    pagina: int = 1,
    por_pagina: int = 50,
    estado: str | None = None,
    tipo_documento_id: uuid.UUID | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> AsientoListResponse:
    q = (
        db.query(CntAsiento)
        .options(joinedload(CntAsiento.lineas))
        .filter(CntAsiento.activo == True)
    )
    if estado:
        q = q.filter(CntAsiento.estado == estado)
    if tipo_documento_id:
        q = q.filter(CntAsiento.tipo_documento_id == tipo_documento_id)
    if fecha_desde:
        q = q.filter(CntAsiento.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(CntAsiento.fecha <= fecha_hasta)

    total = q.count()
    rows = q.order_by(CntAsiento.numero.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    return AsientoListResponse(
        items=[_to_list_item(a, db) for a in rows],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


def obtener(db: Session, id: uuid.UUID) -> AsientoResponse:
    asiento = (
        db.query(CntAsiento)
        .options(joinedload(CntAsiento.lineas))
        .filter(CntAsiento.id == id, CntAsiento.activo == True)
        .first()
    )
    if not asiento:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    return _to_response(asiento, db)


def crear(db: Session, data: AsientoCreate, actor: UsuarioActual) -> AsientoResponse:
    td = db.get(AdmTipoDocumento, data.tipo_documento_id)
    if not td:
        raise HTTPException(status_code=400, detail="Tipo de documento no encontrado")
    if td.modulo != "contabilidad":
        raise HTTPException(status_code=400, detail="Solo se pueden crear manualmente asientos del módulo contabilidad")

    periodo = _buscar_periodo(db, data.fecha)
    moneda_func = _moneda_funcional(db)

    if data.moneda_id != moneda_func.id and not data.trm:
        raise HTTPException(status_code=400, detail="Se requiere TRM para moneda extranjera")

    asiento = CntAsiento(
        id=uuid.uuid4(),
        tipo_documento_id=data.tipo_documento_id,
        fecha=data.fecha,
        periodo_id=periodo.id,
        descripcion=data.descripcion,
        estado="borrador",
        moneda_id=data.moneda_id,
        trm=data.trm if data.moneda_id != moneda_func.id else None,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(asiento)
    db.flush()

    for i, linea_data in enumerate(data.lineas):
        _agregar_linea_interna(db, asiento, linea_data, i + 1, moneda_func)

    db.commit()
    db.refresh(asiento)
    return _to_response(asiento, db)


def actualizar(db: Session, id: uuid.UUID, data: AsientoUpdate, actor: UsuarioActual) -> AsientoResponse:
    asiento = db.query(CntAsiento).filter(CntAsiento.id == id, CntAsiento.activo == True).first()
    if not asiento:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    if asiento.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se pueden modificar asientos en borrador")

    moneda_func = _moneda_funcional(db)

    if data.fecha is not None:
        periodo = _buscar_periodo(db, data.fecha)
        asiento.fecha = data.fecha
        asiento.periodo_id = periodo.id
    if data.descripcion is not None:
        asiento.descripcion = data.descripcion
    if data.moneda_id is not None:
        asiento.moneda_id = data.moneda_id
        asiento.trm = data.trm if data.moneda_id != moneda_func.id else None

    asiento.modificado_por = uuid.UUID(actor.id)
    asiento.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(asiento)
    return _to_response(asiento, db)


# ---------------------------------------------------------------------------
# Líneas
# ---------------------------------------------------------------------------

def _agregar_linea_interna(
    db: Session, asiento: CntAsiento, data: LineaCreate, orden: int, moneda_func: AdmMoneda
) -> CntAsientoLinea:
    cuenta = db.get(CntCuenta, data.cuenta_id)
    if not cuenta:
        raise HTTPException(status_code=400, detail=f"Cuenta {data.cuenta_id} no encontrada")
    if not cuenta.acepta_movimiento:
        raise HTTPException(status_code=400, detail=f"La cuenta {cuenta.codigo} no acepta movimiento (debe ser auxiliar)")
    if cuenta.requiere_tercero and not data.tercero_id:
        raise HTTPException(status_code=400, detail=f"La cuenta {cuenta.codigo} requiere tercero")
    if cuenta.requiere_cc and not data.centro_costo_id:
        raise HTTPException(status_code=400, detail=f"La cuenta {cuenta.codigo} requiere centro de costo")

    trm = asiento.trm
    monto_d = data.debito or Decimal("0")
    monto_c = data.credito or Decimal("0")
    d_func = _calcular_funcional(monto_d, asiento.moneda_id, moneda_func.id, trm) if monto_d else Decimal("0")
    c_func = _calcular_funcional(monto_c, asiento.moneda_id, moneda_func.id, trm) if monto_c else Decimal("0")

    linea = CntAsientoLinea(
        id=uuid.uuid4(),
        asiento_id=asiento.id,
        orden=orden,
        cuenta_id=data.cuenta_id,
        debito=monto_d,
        credito=monto_c,
        debito_funcional=d_func,
        credito_funcional=c_func,
        tercero_id=data.tercero_id,
        centro_costo_id=data.centro_costo_id,
        descripcion=data.descripcion,
    )
    db.add(linea)
    return linea


def agregar_linea(db: Session, asiento_id: uuid.UUID, data: LineaCreate, actor: UsuarioActual) -> LineaResponse:
    asiento = db.query(CntAsiento).options(joinedload(CntAsiento.lineas)).filter(
        CntAsiento.id == asiento_id, CntAsiento.activo == True
    ).first()
    if not asiento:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    if asiento.estado != "borrador":
        raise HTTPException(status_code=409, detail="No se pueden agregar líneas a un asiento publicado")

    moneda_func = _moneda_funcional(db)
    orden = max((l.orden for l in asiento.lineas if l.activo), default=0) + 1
    linea = _agregar_linea_interna(db, asiento, data, orden, moneda_func)
    db.commit()
    db.refresh(linea)
    return _enriquecer_linea(linea, db)


def actualizar_linea(
    db: Session, asiento_id: uuid.UUID, linea_id: uuid.UUID, data: LineaUpdate, actor: UsuarioActual
) -> LineaResponse:
    asiento = db.get(CntAsiento, asiento_id)
    if not asiento or not asiento.activo:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    if asiento.estado != "borrador":
        raise HTTPException(status_code=409, detail="No se pueden modificar líneas de un asiento publicado")

    linea = db.query(CntAsientoLinea).filter(
        CntAsientoLinea.id == linea_id,
        CntAsientoLinea.asiento_id == asiento_id,
        CntAsientoLinea.activo == True,
    ).first()
    if not linea:
        raise HTTPException(status_code=404, detail="Línea no encontrada")

    moneda_func = _moneda_funcional(db)

    if data.cuenta_id is not None:
        cuenta = db.get(CntCuenta, data.cuenta_id)
        if not cuenta or not cuenta.acepta_movimiento:
            raise HTTPException(status_code=400, detail="Cuenta inválida o no acepta movimiento")
        linea.cuenta_id = data.cuenta_id
    else:
        cuenta = db.get(CntCuenta, linea.cuenta_id)

    tercero_final = data.tercero_id if data.tercero_id is not None else linea.tercero_id
    cc_final = data.centro_costo_id if data.centro_costo_id is not None else linea.centro_costo_id
    if cuenta and cuenta.requiere_tercero and not tercero_final:
        raise HTTPException(status_code=400, detail=f"La cuenta {cuenta.codigo} requiere tercero")
    if cuenta and cuenta.requiere_cc and not cc_final:
        raise HTTPException(status_code=400, detail=f"La cuenta {cuenta.codigo} requiere centro de costo")

    if data.debito is not None or data.credito is not None:
        d = data.debito if data.debito is not None else linea.debito
        c = data.credito if data.credito is not None else linea.credito
        linea.debito = d
        linea.credito = c
        linea.debito_funcional = _calcular_funcional(d, asiento.moneda_id, moneda_func.id, asiento.trm) if d else Decimal("0")
        linea.credito_funcional = _calcular_funcional(c, asiento.moneda_id, moneda_func.id, asiento.trm) if c else Decimal("0")

    if data.tercero_id is not None:
        linea.tercero_id = data.tercero_id
    if data.centro_costo_id is not None:
        linea.centro_costo_id = data.centro_costo_id
    if data.descripcion is not None:
        linea.descripcion = data.descripcion

    db.commit()
    db.refresh(linea)
    return _enriquecer_linea(linea, db)


def eliminar_linea(db: Session, asiento_id: uuid.UUID, linea_id: uuid.UUID, actor: UsuarioActual) -> None:
    asiento = db.get(CntAsiento, asiento_id)
    if not asiento or not asiento.activo:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    if asiento.estado != "borrador":
        raise HTTPException(status_code=409, detail="No se pueden eliminar líneas de un asiento publicado")

    linea = db.query(CntAsientoLinea).filter(
        CntAsientoLinea.id == linea_id,
        CntAsientoLinea.asiento_id == asiento_id,
        CntAsientoLinea.activo == True,
    ).first()
    if not linea:
        raise HTTPException(status_code=404, detail="Línea no encontrada")

    linea.activo = False
    db.commit()


# ---------------------------------------------------------------------------
# Publicar
# ---------------------------------------------------------------------------

def publicar(db: Session, id: uuid.UUID, actor: UsuarioActual) -> AsientoResponse:
    # with_for_update() no es compatible con joinedload en PostgreSQL.
    # Primero bloqueamos solo la fila del asiento, luego cargamos líneas por separado.
    asiento = (
        db.query(CntAsiento)
        .filter(CntAsiento.id == id, CntAsiento.activo == True)
        .with_for_update()
        .first()
    )
    if not asiento:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    if asiento.estado != "borrador":
        raise HTTPException(status_code=409, detail="El asiento ya está publicado")

    lineas = (
        db.query(CntAsientoLinea)
        .filter(CntAsientoLinea.asiento_id == id, CntAsientoLinea.activo == True)
        .order_by(CntAsientoLinea.orden)
        .all()
    )
    if len(lineas) < 2:
        raise HTTPException(status_code=400, detail="El asiento debe tener al menos 2 líneas")

    total_d = sum(l.debito for l in lineas)
    total_c = sum(l.credito for l in lineas)
    if total_d != total_c:
        raise HTTPException(
            status_code=400,
            detail=f"El asiento no cuadra: debitos {total_d} != creditos {total_c}"
        )

    periodo = db.get(CntPeriodo, asiento.periodo_id)
    if not periodo or periodo.estado != "abierto":
        raise HTTPException(status_code=400, detail="El período contable no está abierto")

    moneda_func = _moneda_funcional(db)
    if asiento.moneda_id != moneda_func.id and not asiento.trm:
        raise HTTPException(status_code=400, detail="Se requiere TRM para publicar en moneda extranjera")

    for l in lineas:
        cuenta = db.get(CntCuenta, l.cuenta_id)
        if cuenta and cuenta.requiere_tercero and not l.tercero_id:
            raise HTTPException(status_code=400, detail=f"La cuenta {cuenta.codigo} requiere tercero")
        if cuenta and cuenta.requiere_cc and not l.centro_costo_id:
            raise HTTPException(status_code=400, detail=f"La cuenta {cuenta.codigo} requiere centro de costo")

    doc_numero = _generar_documento_numero(db, asiento.tipo_documento_id)
    asiento.documento_numero = doc_numero
    asiento.estado = "publicado"
    asiento.modificado_por = uuid.UUID(actor.id)
    asiento.modificado_en = datetime.now(timezone.utc)

    db.commit()

    # Recargar líneas activas tras el commit para construir el response
    lineas_response = (
        db.query(CntAsientoLinea)
        .filter(CntAsientoLinea.asiento_id == id, CntAsientoLinea.activo == True)
        .order_by(CntAsientoLinea.orden)
        .all()
    )
    db.refresh(asiento)
    td = db.get(AdmTipoDocumento, asiento.tipo_documento_id)
    moneda = db.get(AdmMoneda, asiento.moneda_id)
    total_d = sum(l.debito for l in lineas_response)
    total_c = sum(l.credito for l in lineas_response)
    return AsientoResponse(
        id=asiento.id,
        numero=asiento.numero,
        documento_numero=asiento.documento_numero,
        tipo_documento_id=asiento.tipo_documento_id,
        tipo_documento_codigo=td.codigo if td else "",
        tipo_documento_nombre=td.nombre if td else "",
        fecha=asiento.fecha,
        periodo_id=asiento.periodo_id,
        descripcion=asiento.descripcion,
        documento_origen_id=asiento.documento_origen_id,
        documento_origen_tipo=asiento.documento_origen_tipo,
        estado=asiento.estado,
        moneda_id=asiento.moneda_id,
        moneda_codigo=moneda.codigo if moneda else "",
        trm=asiento.trm,
        asiento_origen_id=asiento.asiento_origen_id,
        total_debito=total_d,
        total_credito=total_c,
        lineas=[_enriquecer_linea(l, db) for l in lineas_response],
        creado_en=asiento.creado_en,
        creado_por=asiento.creado_por,
    )


# ---------------------------------------------------------------------------
# Corregir — edición directa con auditoría (solo asientos manuales AM)
# ---------------------------------------------------------------------------

def corregir(db: Session, id: uuid.UUID, data: AsientoCorregirRequest, actor: UsuarioActual) -> AsientoResponse:
    asiento = (
        db.query(CntAsiento)
        .options(joinedload(CntAsiento.lineas))
        .filter(CntAsiento.id == id, CntAsiento.activo == True)
        .first()
    )
    if not asiento:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    if asiento.estado != "publicado":
        raise HTTPException(status_code=409, detail="Solo se pueden corregir asientos publicados")

    td = db.get(AdmTipoDocumento, asiento.tipo_documento_id)
    if not td or td.codigo != "AM":
        raise HTTPException(status_code=409, detail="Solo se pueden corregir asientos manuales (AM)")

    config = db.query(AdmConfiguracion).filter(AdmConfiguracion.clave == "permitir_correccion_asientos").first()
    if config and config.valor == "false":
        raise HTTPException(status_code=403, detail="La corrección de asientos está deshabilitada en la configuración")

    periodo = db.get(CntPeriodo, asiento.periodo_id)
    if not periodo or periodo.estado != "abierto":
        raise HTTPException(status_code=400, detail="El período del asiento no está abierto")

    lineas_activas = [l for l in asiento.lineas if l.activo]
    moneda_func = _moneda_funcional(db)

    # Guardar snapshot antes de modificar
    snapshot = [
        {
            "orden": l.orden,
            "cuenta_id": str(l.cuenta_id),
            "debito": str(l.debito),
            "credito": str(l.credito),
            "tercero_id": str(l.tercero_id) if l.tercero_id else None,
            "centro_costo_id": str(l.centro_costo_id) if l.centro_costo_id else None,
            "descripcion": l.descripcion,
        }
        for l in sorted(lineas_activas, key=lambda x: x.orden)
    ]
    db.add(CntAsientoCorreccion(
        id=uuid.uuid4(),
        asiento_id=asiento.id,
        usuario_id=uuid.UUID(actor.id),
        motivo=data.motivo,
        snapshot_lineas=snapshot,
    ))

    # Actualizar descripción si viene
    if data.descripcion:
        asiento.descripcion = data.descripcion.strip()

    # Reemplazar líneas
    if data.lineas:
        for l in lineas_activas:
            l.activo = False
        trm = asiento.trm or Decimal("1")
        for i, linea in enumerate(data.lineas):
            d_func = (linea.debito * trm).quantize(Decimal("0.0001")) if asiento.moneda_id != moneda_func.id else linea.debito
            c_func = (linea.credito * trm).quantize(Decimal("0.0001")) if asiento.moneda_id != moneda_func.id else linea.credito
            db.add(CntAsientoLinea(
                id=uuid.uuid4(),
                asiento_id=asiento.id,
                orden=i + 1,
                cuenta_id=linea.cuenta_id,
                debito=linea.debito,
                credito=linea.credito,
                debito_funcional=d_func,
                credito_funcional=c_func,
                tercero_id=linea.tercero_id,
                centro_costo_id=linea.centro_costo_id,
                descripcion=linea.descripcion,
            ))

    db.commit()
    db.refresh(asiento)
    return _to_response(asiento, db)
