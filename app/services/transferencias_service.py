import uuid
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.bancos import BanCuenta, BanTransferencia
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntPeriodo, CntCuenta
from app.models.admin import AdmTipoDocumento, AdmConsecutivo, AdmMoneda
from app.schemas.bancos import TransferenciaResponse, TransferenciaListItem


def _resp(db: Session, t: BanTransferencia) -> TransferenciaResponse:
    o = db.get(BanCuenta, t.cuenta_origen_id)
    d = db.get(BanCuenta, t.cuenta_destino_id)
    return TransferenciaResponse(
        id=t.id, numero=t.numero, fecha=t.fecha,
        cuenta_origen_id=t.cuenta_origen_id, cuenta_origen_nombre=(f"{o.nombre} ({o.numero})" if o else None),
        cuenta_destino_id=t.cuenta_destino_id, cuenta_destino_nombre=(f"{d.nombre} ({d.numero})" if d else None),
        valor=t.valor, descripcion=t.descripcion, estado=t.estado, asiento_id=t.asiento_id,
    )


def _generar_numero(db: Session):
    td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "TRB").first()
    if not td:
        raise HTTPException(status_code=400, detail="Tipo de documento TRB no configurado")
    cons = db.query(AdmConsecutivo).filter(AdmConsecutivo.tipo_documento_id == td.id).with_for_update().first()
    if not cons:
        raise HTTPException(status_code=400, detail="No hay consecutivo para transferencias")
    siguiente = max(cons.numero_actual + 1, cons.numero_inicio)
    cons.numero_actual = siguiente
    return f"{cons.prefijo or ''}{str(siguiente).zfill(cons.longitud_minima)}", td.id


def _validar(db: Session, cuenta_origen_id, cuenta_destino_id, valor):
    if cuenta_origen_id == cuenta_destino_id:
        raise HTTPException(status_code=400, detail="Las cuentas de origen y destino deben ser distintas")
    if valor is None or valor <= 0:
        raise HTTPException(status_code=400, detail="El valor debe ser mayor que cero")
    o = db.query(BanCuenta).filter(BanCuenta.id == cuenta_origen_id, BanCuenta.activo == True).first()
    d = db.query(BanCuenta).filter(BanCuenta.id == cuenta_destino_id, BanCuenta.activo == True).first()
    if not o or not d:
        raise HTTPException(status_code=400, detail="Cuenta bancaria no encontrada")
    if not o.cuenta_contable_id or not d.cuenta_contable_id:
        raise HTTPException(status_code=400, detail="Ambas cuentas deben tener cuenta contable parametrizada")
    if (o.moneda_id or None) != (d.moneda_id or None):
        raise HTTPException(status_code=400, detail="Las cuentas deben ser de la misma moneda")
    return o, d


def _periodo(db: Session, fecha):
    p = db.query(CntPeriodo).filter(
        CntPeriodo.fecha_inicio <= fecha, CntPeriodo.fecha_cierre >= fecha, CntPeriodo.activo == True
    ).first()
    if not p:
        raise HTTPException(status_code=400, detail=f"No existe período contable para la fecha {fecha}")
    return p


def listar(db: Session, fecha_desde: str | None = None, fecha_hasta: str | None = None):
    q = db.query(BanTransferencia).filter(BanTransferencia.activo == True)
    if fecha_desde:
        q = q.filter(BanTransferencia.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(BanTransferencia.fecha <= fecha_hasta)
    rows = q.order_by(BanTransferencia.fecha.desc(), BanTransferencia.numero.desc()).all()
    out = []
    for t in rows:
        o = db.get(BanCuenta, t.cuenta_origen_id)
        d = db.get(BanCuenta, t.cuenta_destino_id)
        out.append(TransferenciaListItem(
            id=t.id, numero=t.numero, fecha=t.fecha,
            cuenta_origen_nombre=(f"{o.nombre} ({o.numero})" if o else None),
            cuenta_destino_nombre=(f"{d.nombre} ({d.numero})" if d else None),
            valor=t.valor, estado=t.estado,
        ))
    return out


def obtener(db: Session, id: uuid.UUID):
    t = db.query(BanTransferencia).filter(BanTransferencia.id == id, BanTransferencia.activo == True).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    return _resp(db, t)


def crear(db: Session, data, actor):
    _validar(db, data.cuenta_origen_id, data.cuenta_destino_id, data.valor)
    periodo = _periodo(db, data.fecha)
    numero, _ = _generar_numero(db)
    t = BanTransferencia(
        id=uuid.uuid4(), numero=numero, fecha=data.fecha, periodo_id=periodo.id,
        cuenta_origen_id=data.cuenta_origen_id, cuenta_destino_id=data.cuenta_destino_id,
        valor=data.valor, descripcion=data.descripcion, estado="borrador",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _resp(db, t)


def actualizar(db: Session, id: uuid.UUID, data, actor):
    t = db.query(BanTransferencia).filter(BanTransferencia.id == id, BanTransferencia.activo == True).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    if t.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se pueden editar transferencias en borrador")
    _validar(db, data.cuenta_origen_id, data.cuenta_destino_id, data.valor)
    periodo = _periodo(db, data.fecha)
    t.fecha = data.fecha
    t.periodo_id = periodo.id
    t.cuenta_origen_id = data.cuenta_origen_id
    t.cuenta_destino_id = data.cuenta_destino_id
    t.valor = data.valor
    t.descripcion = data.descripcion
    t.modificado_por = uuid.UUID(actor.id)
    t.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(t)
    return _resp(db, t)


def _crear_asiento(db: Session, t: BanTransferencia, actor):
    o = db.get(BanCuenta, t.cuenta_origen_id)
    d = db.get(BanCuenta, t.cuenta_destino_id)
    td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "TRB").first()
    moneda_func = db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.activo == True).first()
    asiento = CntAsiento(
        id=uuid.uuid4(), tipo_documento_id=td.id if td else None, documento_numero=t.numero,
        fecha=t.fecha, periodo_id=t.periodo_id,
        descripcion=f"TRANSFERENCIA {t.numero} — {o.nombre} a {d.nombre}",
        estado="borrador", moneda_id=(o.moneda_id or (moneda_func.id if moneda_func else None)),
        documento_origen_id=t.id, documento_origen_tipo="ban_transferencia",
        creado_por=uuid.UUID(actor.id),
    )
    db.add(asiento)
    db.flush()
    movimientos = [(d.cuenta_contable_id, t.valor, Decimal("0")), (o.cuenta_contable_id, Decimal("0"), t.valor)]
    for orden, (cta_id, deb, cred) in enumerate(movimientos, start=1):
        db.add(CntAsientoLinea(
            id=uuid.uuid4(), asiento_id=asiento.id, orden=orden, cuenta_id=cta_id,
            debito=deb, credito=cred, debito_funcional=deb, credito_funcional=cred,
        ))
    return asiento


def contabilizar(db: Session, id: uuid.UUID, actor):
    t = db.query(BanTransferencia).filter(BanTransferencia.id == id, BanTransferencia.activo == True).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    if t.estado != "borrador":
        raise HTTPException(status_code=409, detail="La transferencia ya está contabilizada o anulada")
    periodo = db.get(CntPeriodo, t.periodo_id)
    if not periodo or periodo.estado != "abierto":
        raise HTTPException(status_code=400, detail="El período contable no está abierto")
    _validar(db, t.cuenta_origen_id, t.cuenta_destino_id, t.valor)
    asiento = _crear_asiento(db, t, actor)
    asiento.estado = "publicado"
    t.asiento_id = asiento.id
    t.estado = "contabilizado"
    t.modificado_por = uuid.UUID(actor.id)
    t.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(t)
    return _resp(db, t)


def anular(db: Session, id: uuid.UUID, motivo: str, actor):
    t = db.query(BanTransferencia).filter(BanTransferencia.id == id, BanTransferencia.activo == True).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    if t.estado == "anulado":
        raise HTTPException(status_code=409, detail="La transferencia ya está anulada")
    if t.estado == "contabilizado" and t.asiento_id:
        periodo = db.get(CntPeriodo, t.periodo_id)
        if not periodo or periodo.estado != "abierto":
            raise HTTPException(status_code=400, detail="El período contable no está abierto")
        orig = db.get(CntAsiento, t.asiento_id)
        if orig:
            lineas = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == orig.id).all()
            td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "ANU").first()
            contra = CntAsiento(
                id=uuid.uuid4(), tipo_documento_id=td.id if td else orig.tipo_documento_id,
                documento_numero=f"ANU-{orig.documento_numero}", fecha=date.today(), periodo_id=t.periodo_id,
                descripcion=f"ANULACION TRANSFERENCIA {t.numero} — {motivo}", estado="publicado",
                moneda_id=orig.moneda_id, documento_origen_id=t.id,
                documento_origen_tipo="ban_transferencia_anulacion", creado_por=uuid.UUID(actor.id),
            )
            db.add(contra)
            db.flush()
            for i, l in enumerate(lineas, start=1):
                db.add(CntAsientoLinea(
                    id=uuid.uuid4(), asiento_id=contra.id, orden=i, cuenta_id=l.cuenta_id,
                    debito=l.credito, credito=l.debito,
                    debito_funcional=l.credito_funcional, credito_funcional=l.debito_funcional,
                ))
    t.estado = "anulado"
    t.modificado_por = uuid.UUID(actor.id)
    t.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(t)
    return _resp(db, t)


def asiento(db: Session, id: uuid.UUID):
    from app.schemas.facturacion import PreviewAsientoResponse, PreviewAsientoLinea
    t = db.query(BanTransferencia).filter(BanTransferencia.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    o = db.get(BanCuenta, t.cuenta_origen_id)
    d = db.get(BanCuenta, t.cuenta_destino_id)
    if t.asiento_id:
        a = db.get(CntAsiento, t.asiento_id)
        lineas = db.query(CntAsientoLinea).filter(CntAsientoLinea.asiento_id == t.asiento_id).order_by(CntAsientoLinea.orden).all()
        out = []
        for l in lineas:
            c = db.get(CntCuenta, l.cuenta_id)
            out.append(PreviewAsientoLinea(
                cuenta_codigo=c.codigo if c else None, cuenta_nombre=c.nombre if c else None,
                tercero_nombre=None, centro_costo=None, debito=l.debito, credito=l.credito,
            ))
        td_ = sum((l.debito for l in lineas), Decimal("0"))
        tc_ = sum((l.credito for l in lineas), Decimal("0"))
        return PreviewAsientoResponse(
            lineas=out, total_debito=td_, total_credito=tc_, cuadra=abs(td_ - tc_) <= Decimal("0.01"),
            moneda_codigo=None, avisos=[], asiento_numero=a.numero if a else None,
        )
    cd = db.get(CntCuenta, d.cuenta_contable_id) if d and d.cuenta_contable_id else None
    co = db.get(CntCuenta, o.cuenta_contable_id) if o and o.cuenta_contable_id else None
    lineas = [
        PreviewAsientoLinea(cuenta_codigo=cd.codigo if cd else None, cuenta_nombre=cd.nombre if cd else "(sin cuenta)",
                            tercero_nombre=None, centro_costo=None, debito=t.valor, credito=Decimal("0")),
        PreviewAsientoLinea(cuenta_codigo=co.codigo if co else None, cuenta_nombre=co.nombre if co else "(sin cuenta)",
                            tercero_nombre=None, centro_costo=None, debito=Decimal("0"), credito=t.valor),
    ]
    return PreviewAsientoResponse(lineas=lineas, total_debito=t.valor, total_credito=t.valor, cuadra=True, moneda_codigo=None, avisos=[])
