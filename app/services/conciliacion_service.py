"""Conciliación bancaria (Fase 1): extractos + emparejamiento contra el libro."""
import csv
import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.bancos import BanCuenta, BanExtracto, BanExtractoLinea
from app.models.contabilidad import CntAsiento, CntAsientoLinea
from app.schemas.auth import UsuarioActual


def _cuenta(db, cuenta_id):
    c = db.query(BanCuenta).filter(BanCuenta.id == cuenta_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    return c


def crear_extracto(db, data, actor):
    c = _cuenta(db, data.cuenta_id)
    if not c.cuenta_contable_id:
        raise HTTPException(status_code=400, detail="La cuenta bancaria no tiene cuenta contable parametrizada")
    e = BanExtracto(
        id=uuid.uuid4(), cuenta_id=c.id, fecha_desde=data.fecha_desde,
        fecha_hasta=data.fecha_hasta, saldo_final=data.saldo_final or Decimal("0"),
        estado="abierta", creado_por=uuid.UUID(actor.id),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _detalle(db, e)


def listar_extractos(db, cuenta_id=None):
    q = db.query(BanExtracto).filter(BanExtracto.activo == True)
    if cuenta_id:
        q = q.filter(BanExtracto.cuenta_id == cuenta_id)
    out = []
    for e in q.order_by(BanExtracto.fecha_hasta.desc()).all():
        c = db.get(BanCuenta, e.cuenta_id)
        total = db.query(BanExtractoLinea).filter(BanExtractoLinea.extracto_id == e.id).count()
        pend = db.query(BanExtractoLinea).filter(BanExtractoLinea.extracto_id == e.id, BanExtractoLinea.conciliado == False).count()
        out.append({
            "id": str(e.id), "cuenta_id": str(e.cuenta_id),
            "cuenta_nombre": f"{c.nombre} ({c.numero})" if c else None,
            "fecha_desde": e.fecha_desde.isoformat(), "fecha_hasta": e.fecha_hasta.isoformat(),
            "saldo_final": str(e.saldo_final), "estado": e.estado,
            "lineas": total, "pendientes": pend,
        })
    return out


def _saldo_libro(db, cuenta: BanCuenta, hasta: date) -> Decimal:
    """Saldo contable de la cuenta (asientos publicados) hasta la fecha."""
    filas = (
        db.query(CntAsientoLinea.debito, CntAsientoLinea.credito)
        .join(CntAsiento, CntAsientoLinea.asiento_id == CntAsiento.id)
        .filter(CntAsientoLinea.cuenta_id == cuenta.cuenta_contable_id,
                CntAsiento.estado == "publicado", CntAsiento.fecha <= hasta)
        .all()
    )
    return sum((d - c for d, c in filas), Decimal("0"))


def _detalle(db, e: BanExtracto):
    c = db.get(BanCuenta, e.cuenta_id)
    lineas = db.query(BanExtractoLinea).filter(BanExtractoLinea.extracto_id == e.id).order_by(BanExtractoLinea.fecha, BanExtractoLinea.id).all()
    items = [{
        "id": str(l.id), "fecha": l.fecha.isoformat(), "descripcion": l.descripcion,
        "referencia": l.referencia, "valor": str(l.valor), "conciliado": l.conciliado,
        "asiento_linea_id": str(l.asiento_linea_id) if l.asiento_linea_id else None,
    } for l in lineas]
    conc = sum((l.valor for l in lineas if l.conciliado), Decimal("0"))
    noconc = sum((l.valor for l in lineas if not l.conciliado), Decimal("0"))
    saldo_libro = _saldo_libro(db, c, e.fecha_hasta) if c and c.cuenta_contable_id else Decimal("0")
    return {
        "id": str(e.id), "cuenta_id": str(e.cuenta_id),
        "cuenta_nombre": f"{c.nombre} ({c.numero})" if c else None,
        "cuenta_contable_codigo": (db_get_codigo(db, c)),
        "fecha_desde": e.fecha_desde.isoformat(), "fecha_hasta": e.fecha_hasta.isoformat(),
        "saldo_final": str(e.saldo_final), "estado": e.estado,
        "lineas": items,
        "resumen": {
            "saldo_extracto": str(e.saldo_final),
            "saldo_libro": str(saldo_libro),
            "diferencia": str(e.saldo_final - saldo_libro),
            "conciliado": str(conc), "no_conciliado": str(noconc),
            "lineas_total": len(lineas),
            "lineas_conciliadas": sum(1 for l in lineas if l.conciliado),
        },
    }


def db_get_codigo(db, cuenta):
    from app.models.contabilidad import CntCuenta
    if cuenta and cuenta.cuenta_contable_id:
        cc = db.get(CntCuenta, cuenta.cuenta_contable_id)
        return cc.codigo if cc else None
    return None


def obtener_extracto(db, extracto_id):
    e = db.query(BanExtracto).filter(BanExtracto.id == extracto_id, BanExtracto.activo == True).first()
    if not e:
        raise HTTPException(status_code=404, detail="Extracto no encontrado")
    return _detalle(db, e)


def eliminar_extracto(db, extracto_id, actor):
    e = db.query(BanExtracto).filter(BanExtracto.id == extracto_id, BanExtracto.activo == True).first()
    if not e:
        raise HTTPException(status_code=404, detail="Extracto no encontrado")
    e.activo = False
    e.modificado_por = uuid.UUID(actor.id)
    db.commit()
    return {"mensaje": "Extracto eliminado"}


def agregar_linea(db, extracto_id, data, actor):
    e = db.query(BanExtracto).filter(BanExtracto.id == extracto_id, BanExtracto.activo == True).first()
    if not e:
        raise HTTPException(status_code=404, detail="Extracto no encontrado")
    if e.estado == "cerrada":
        raise HTTPException(status_code=409, detail="El extracto está cerrado")
    l = BanExtractoLinea(
        id=uuid.uuid4(), extracto_id=e.id, fecha=data.fecha,
        descripcion=data.descripcion, referencia=data.referencia, valor=data.valor,
    )
    db.add(l)
    db.commit()
    return _detalle(db, e)


def eliminar_linea(db, linea_id, actor):
    l = db.query(BanExtractoLinea).filter(BanExtractoLinea.id == linea_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Línea no encontrada")
    ext_id = l.extracto_id
    db.delete(l)
    db.commit()
    e = db.get(BanExtracto, ext_id)
    return _detalle(db, e)


def _parse_fecha(s: str) -> date:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha no reconocida: {s}")


def _parse_valor(s: str) -> Decimal:
    s = (s or "").strip().replace("$", "").replace(" ", "")
    if not s:
        return Decimal("0")
    # Formato colombiano: 1.234.567,89  → 1234567.89
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Valor no reconocido: {s}")


def importar_csv(db, extracto_id, contenido: bytes, actor):
    e = db.query(BanExtracto).filter(BanExtracto.id == extracto_id, BanExtracto.activo == True).first()
    if not e:
        raise HTTPException(status_code=404, detail="Extracto no encontrado")
    if e.estado == "cerrada":
        raise HTTPException(status_code=409, detail="El extracto está cerrado")

    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")
    delim = ";" if texto.count(";") > texto.count(",") else ","
    reader = csv.DictReader(io.StringIO(texto), delimiter=delim)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV vacío o sin encabezados")
    cols = {c.lower().strip(): c for c in reader.fieldnames}

    def col(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    c_fecha = col("fecha", "date")
    c_desc = col("descripcion", "descripción", "concepto", "detalle", "description")
    c_valor = col("valor", "monto", "importe", "amount")
    c_debito = col("debito", "débito", "debe", "salida", "retiro")
    c_credito = col("credito", "crédito", "haber", "entrada", "consignacion", "consignación")
    c_ref = col("referencia", "ref", "documento", "comprobante")
    if not c_fecha or not c_desc or (not c_valor and not (c_debito or c_credito)):
        raise HTTPException(status_code=400, detail="El CSV debe tener columnas: fecha, descripcion y valor (o debito/credito)")

    # Importar reemplaza: se limpian las líneas previas del extracto (evita duplicados al reimportar)
    db.query(BanExtractoLinea).filter(BanExtractoLinea.extracto_id == e.id).delete()
    db.flush()

    creadas = 0
    errores = []
    for i, row in enumerate(reader, start=2):
        try:
            f = _parse_fecha(row.get(c_fecha, ""))
            desc = (row.get(c_desc, "") or "").strip()[:300] or "(sin descripción)"
            if c_valor:
                valor = _parse_valor(row.get(c_valor, ""))
            else:
                deb = _parse_valor(row.get(c_debito, "")) if c_debito else Decimal("0")
                cred = _parse_valor(row.get(c_credito, "")) if c_credito else Decimal("0")
                valor = cred - deb  # entra positivo, sale negativo
            if valor == 0:
                continue
            ref = (row.get(c_ref, "") or "").strip()[:100] if c_ref else None
            db.add(BanExtractoLinea(id=uuid.uuid4(), extracto_id=e.id, fecha=f, descripcion=desc, referencia=ref, valor=valor))
            creadas += 1
        except Exception as ex:
            errores.append(f"Fila {i}: {ex}")
            if len(errores) > 20:
                break
    db.commit()
    res = _detalle(db, e)
    res["importacion"] = {"creadas": creadas, "errores": errores}
    return res


def libro_no_conciliado(db, extracto_id):
    """Movimientos del libro de la cuenta (en el rango) con su estado de conciliación."""
    e = db.query(BanExtracto).filter(BanExtracto.id == extracto_id, BanExtracto.activo == True).first()
    if not e:
        raise HTTPException(status_code=404, detail="Extracto no encontrado")
    c = db.get(BanCuenta, e.cuenta_id)
    if not c or not c.cuenta_contable_id:
        return []
    # ids de asiento_linea ya conciliadas (en cualquier extracto)
    conc_ids = set(
        r[0] for r in db.query(BanExtractoLinea.asiento_linea_id)
        .filter(BanExtractoLinea.asiento_linea_id.isnot(None)).all()
    )
    filas = (
        db.query(CntAsientoLinea, CntAsiento)
        .join(CntAsiento, CntAsientoLinea.asiento_id == CntAsiento.id)
        .filter(CntAsientoLinea.cuenta_id == c.cuenta_contable_id,
                CntAsiento.estado == "publicado",
                CntAsiento.fecha >= e.fecha_desde, CntAsiento.fecha <= e.fecha_hasta)
        .order_by(CntAsiento.fecha, CntAsiento.numero)
        .all()
    )
    out = []
    for l, a in filas:
        out.append({
            "asiento_linea_id": str(l.id),
            "fecha": a.fecha.isoformat(),
            "documento_numero": a.documento_numero,
            "asiento_numero": a.numero,
            "descripcion": a.descripcion,
            "valor": str(l.debito - l.credito),  # + entra / − sale
            "conciliado": l.id in conc_ids,
        })
    return out


def conciliar(db, extracto_linea_id, asiento_linea_id, actor):
    l = db.query(BanExtractoLinea).filter(BanExtractoLinea.id == extracto_linea_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Línea de extracto no encontrada")
    al = db.query(CntAsientoLinea).filter(CntAsientoLinea.id == asiento_linea_id).first()
    if not al:
        raise HTTPException(status_code=404, detail="Movimiento del libro no encontrado")
    # ¿ya conciliada esa línea de libro por otra?
    otra = db.query(BanExtractoLinea).filter(
        BanExtractoLinea.asiento_linea_id == asiento_linea_id,
        BanExtractoLinea.id != extracto_linea_id,
    ).first()
    if otra:
        raise HTTPException(status_code=409, detail="Ese movimiento del libro ya está conciliado con otra línea")
    l.asiento_linea_id = asiento_linea_id
    l.conciliado = True
    l.conciliado_en = datetime.now(timezone.utc)
    l.conciliado_por = uuid.UUID(actor.id)
    db.commit()
    return _detalle(db, db.get(BanExtracto, l.extracto_id))


def desconciliar(db, extracto_linea_id, actor):
    l = db.query(BanExtractoLinea).filter(BanExtractoLinea.id == extracto_linea_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Línea de extracto no encontrada")
    l.asiento_linea_id = None
    l.conciliado = False
    l.conciliado_en = None
    l.conciliado_por = None
    db.commit()
    return _detalle(db, db.get(BanExtracto, l.extracto_id))


def cambiar_estado(db, extracto_id, estado, actor):
    e = db.query(BanExtracto).filter(BanExtracto.id == extracto_id, BanExtracto.activo == True).first()
    if not e:
        raise HTTPException(status_code=404, detail="Extracto no encontrado")
    if estado not in ("abierta", "cerrada"):
        raise HTTPException(status_code=400, detail="Estado inválido")
    e.estado = estado
    e.modificado_por = uuid.UUID(actor.id)
    db.commit()
    return _detalle(db, e)
