"""Documentos de transporte marítimo: MBL, HBL y contenedores.

El HBL tiene ciclo de vida propio porque en exportación lo emite Universal Cargo
(BORRADOR → EMITIDA → ANULADA), mientras que en importación llega ya emitido por
el agente de origen y se registra como RECIBIDO.
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auditoria import registrar as audit
from app.models.adm import AdmTercero
from app.models.admin import AdmUsuario
from app.models.ope import (
    OpeAerolinea, OpeAeropuerto, OpeBlCargo, OpeContenedor, OpeCotizacion,
    OpeHbl, OpeHblContenedor, OpeMbl, OpeOperacion,
)
from app.schemas.auth import UsuarioActual
from app.schemas.ope_maritimo import (
    ContenedorCreate, ContenedorResponse, ContenedorUpdate,
    HblCreate, HblResponse, HblUpdate,
    MaritimoBusquedaItem, MaritimoCarpetaResponse,
    MblCreate, MblResponse, MblUpdate,
)

_CAMPOS_BL = [
    "booking_no", "export_references", "referencia_cliente",
    "shipper_id", "shipper_texto", "consignee_id", "consignee_texto",
    "notify_id", "notify_texto",
    "pre_carriage_by", "place_of_receipt", "puerto_embarque_id",
    "puerto_descarga_id", "place_of_delivery", "onward_inland_routing",
    "buque", "viaje",
    "fecha_emision", "lugar_emision", "shipped_on_board", "etd", "eta",
    "fecha_arribo",
    "termino", "tipo_carga", "tipo_pago_flete", "freight_to_be_paid_at",
    "num_originales", "declared_value",
    "say_total", "marcas", "descripcion_mercancia", "bultos_cantidad",
    "bultos_clase", "carrier_receipt", "peso_bruto_kg", "cbm", "notas",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _operacion(db: Session, operacion_id: uuid.UUID) -> OpeOperacion:
    op = db.query(OpeOperacion).filter(
        OpeOperacion.id == operacion_id, OpeOperacion.activo == True
    ).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operación no encontrada")
    return op


def _verificar_editable(op: OpeOperacion) -> None:
    if op.estado in ("CERRADA", "CANCELADA"):
        raise HTTPException(
            status_code=400,
            detail=f"La operación {op.numero} está {op.estado.lower()}: no admite cambios.",
        )


def _nombre(db: Session, tid) -> str | None:
    if not tid:
        return None
    t = db.get(AdmTercero, tid)
    return t.razon_social if t else None


def _usuario(db: Session, uid) -> str | None:
    if not uid:
        return None
    u = db.get(AdmUsuario, uid)
    return f"{u.nombre} {u.apellido}" if u else None


def _puerto(db: Session, pid) -> str | None:
    if not pid:
        return None
    p = db.get(OpeAeropuerto, pid)
    return f"{p.codigo_iata} · {p.nombre}" if p else None


def _aplicar(destino, data, campos: list[str], solo_enviados: bool) -> None:
    dump = data.model_dump(exclude_unset=True) if solo_enviados else data.model_dump()
    for campo in campos:
        if campo in dump:
            setattr(destino, campo, dump[campo])


# ---------------------------------------------------------------------------
# Armado de respuestas
# ---------------------------------------------------------------------------

def _mbl_resp(db: Session, m: OpeMbl) -> MblResponse:
    r = MblResponse.model_validate(m)
    nav = db.get(OpeAerolinea, m.naviera_id) if m.naviera_id else None
    r.naviera_nombre = nav.nombre if nav else None
    r.puerto_embarque = _puerto(db, m.puerto_embarque_id)
    r.puerto_descarga = _puerto(db, m.puerto_descarga_id)
    r.shipper_nombre = _nombre(db, m.shipper_id)
    r.consignee_nombre = _nombre(db, m.consignee_id)
    r.total_hbls = db.query(OpeHbl).filter(OpeHbl.mbl_id == m.id).count()
    r.total_contenedores = db.query(OpeContenedor).filter(OpeContenedor.mbl_id == m.id).count()
    return r


def _hbl_resp(db: Session, h: OpeHbl) -> HblResponse:
    r = HblResponse.model_validate(h)
    mbl = db.get(OpeMbl, h.mbl_id) if h.mbl_id else None
    r.mbl_numero = mbl.numero_bl if mbl else None
    cot = db.get(OpeCotizacion, h.cotizacion_id) if h.cotizacion_id else None
    r.cotizacion_numero = cot.numero if cot else None
    r.cliente_nombre = _nombre(db, cot.cliente_id) if cot else None
    r.puerto_embarque = _puerto(db, h.puerto_embarque_id)
    r.puerto_descarga = _puerto(db, h.puerto_descarga_id)
    r.shipper_nombre = _nombre(db, h.shipper_id)
    r.consignee_nombre = _nombre(db, h.consignee_id)
    r.emisor_nombre = _nombre(db, h.emisor_id)
    r.emitido_por_nombre = _usuario(db, h.emitido_por)
    r.anulado_por_nombre = _usuario(db, h.anulado_por)
    r.contenedores = [
        {
            "contenedor_id": l.contenedor_id, "piezas": l.piezas,
            "peso_kg": l.peso_kg, "cbm": l.cbm,
            "numero": l.contenedor.numero if l.contenedor else "",
            "sello": l.contenedor.sello if l.contenedor else None,
            "tipo": l.contenedor.tipo if l.contenedor else None,
        }
        for l in h.contenedores
    ]
    r.cargos = [
        {"orden": c.orden, "concepto": c.concepto, "tarifa": c.tarifa,
         "unidad": c.unidad, "moneda": c.moneda, "valor": c.valor, "pago": c.pago}
        for c in h.cargos
    ]
    return r


def _cont_resp(db: Session, c: OpeContenedor) -> ContenedorResponse:
    r = ContenedorResponse.model_validate(c)
    mbl = db.get(OpeMbl, c.mbl_id) if c.mbl_id else None
    r.mbl_numero = mbl.numero_bl if mbl else None
    r.hbls_numeros = [l.hbl.numero_hbl for l in c.hbls if l.hbl]
    return r


# ---------------------------------------------------------------------------
# Carpeta
# ---------------------------------------------------------------------------

def obtener_carpeta(db: Session, operacion_id: uuid.UUID) -> MaritimoCarpetaResponse:
    op = _operacion(db, operacion_id)
    return MaritimoCarpetaResponse(
        operacion_id=op.id,
        mbls=[_mbl_resp(db, m) for m in sorted(op.mbls, key=lambda x: x.numero_bl)],
        hbls=[_hbl_resp(db, h) for h in sorted(op.hbls, key=lambda x: x.numero_hbl)],
        contenedores=[_cont_resp(db, c) for c in sorted(op.contenedores, key=lambda x: x.numero)],
    )


# ---------------------------------------------------------------------------
# MBL
# ---------------------------------------------------------------------------

def crear_mbl(db: Session, operacion_id: uuid.UUID, data: MblCreate, actor: UsuarioActual) -> MblResponse:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    actor_id = uuid.UUID(actor.id)
    m = OpeMbl(operacion_id=op.id, numero_bl=data.numero_bl, creado_por=actor_id)
    _aplicar(m, data, _CAMPOS_BL + ["naviera_id", "agente_destino", "tara_kg", "free_days"], False)
    db.add(m)
    db.flush()
    audit(db, "ope_mbl", m.id, "INSERT", actor_id,
          contexto={"operacion": op.numero, "numero_bl": m.numero_bl})
    db.commit()
    db.refresh(m)
    return _mbl_resp(db, m)


def actualizar_mbl(db: Session, operacion_id: uuid.UUID, mbl_id: uuid.UUID,
                   data: MblUpdate, actor: UsuarioActual) -> MblResponse:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    m = db.query(OpeMbl).filter(OpeMbl.id == mbl_id, OpeMbl.operacion_id == op.id).first()
    if not m:
        raise HTTPException(status_code=404, detail="MBL no encontrado")
    actor_id = uuid.UUID(actor.id)
    _aplicar(m, data, _CAMPOS_BL + ["numero_bl", "naviera_id", "agente_destino", "tara_kg", "free_days"], True)
    m.modificado_por = actor_id
    m.modificado_en = datetime.now(timezone.utc)
    audit(db, "ope_mbl", m.id, "UPDATE", actor_id, contexto={"numero_bl": m.numero_bl})
    db.commit()
    db.refresh(m)
    return _mbl_resp(db, m)


def eliminar_mbl(db: Session, operacion_id: uuid.UUID, mbl_id: uuid.UUID, actor: UsuarioActual) -> None:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    m = db.query(OpeMbl).filter(OpeMbl.id == mbl_id, OpeMbl.operacion_id == op.id).first()
    if not m:
        raise HTTPException(status_code=404, detail="MBL no encontrado")
    hijos = db.query(OpeHbl).filter(OpeHbl.mbl_id == m.id).count()
    if hijos:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: el MBL tiene {hijos} HBL asociado(s).",
        )
    audit(db, "ope_mbl", m.id, "DELETE", uuid.UUID(actor.id), contexto={"numero_bl": m.numero_bl})
    db.delete(m)
    db.commit()


# ---------------------------------------------------------------------------
# Contenedores
# ---------------------------------------------------------------------------

def crear_contenedor(db: Session, operacion_id: uuid.UUID, data: ContenedorCreate,
                     actor: UsuarioActual) -> ContenedorResponse:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    actor_id = uuid.UUID(actor.id)
    c = OpeContenedor(operacion_id=op.id, numero=data.numero, creado_por=actor_id)
    _aplicar(c, data, ["mbl_id", "sello", "tipo", "tara_kg", "peso_bruto_kg", "cbm",
                       "fecha_devolucion", "notas"], False)
    db.add(c)
    db.flush()
    audit(db, "ope_contenedor", c.id, "INSERT", actor_id,
          contexto={"operacion": op.numero, "numero": c.numero})
    db.commit()
    db.refresh(c)
    return _cont_resp(db, c)


def actualizar_contenedor(db: Session, operacion_id: uuid.UUID, cont_id: uuid.UUID,
                          data: ContenedorUpdate, actor: UsuarioActual) -> ContenedorResponse:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    c = db.query(OpeContenedor).filter(
        OpeContenedor.id == cont_id, OpeContenedor.operacion_id == op.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contenedor no encontrado")
    _aplicar(c, data, ["numero", "mbl_id", "sello", "tipo", "tara_kg", "peso_bruto_kg",
                       "cbm", "fecha_devolucion", "notas"], True)
    c.modificado_por = uuid.UUID(actor.id)
    c.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return _cont_resp(db, c)


def eliminar_contenedor(db: Session, operacion_id: uuid.UUID, cont_id: uuid.UUID,
                        actor: UsuarioActual) -> None:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    c = db.query(OpeContenedor).filter(
        OpeContenedor.id == cont_id, OpeContenedor.operacion_id == op.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contenedor no encontrado")
    usos = db.query(OpeHblContenedor).filter(OpeHblContenedor.contenedor_id == c.id).count()
    if usos:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: el contenedor está en {usos} HBL.",
        )
    db.delete(c)
    db.commit()


# ---------------------------------------------------------------------------
# HBL
# ---------------------------------------------------------------------------

def _sincronizar_contenedores(db: Session, h: OpeHbl, enlaces) -> None:
    """Reemplaza los contenedores del HBL. Valida que sean de la misma operación."""
    db.query(OpeHblContenedor).filter(OpeHblContenedor.hbl_id == h.id).delete()
    vistos = set()
    for e in enlaces or []:
        if e.contenedor_id in vistos:
            continue
        vistos.add(e.contenedor_id)
        c = db.get(OpeContenedor, e.contenedor_id)
        if not c or c.operacion_id != h.operacion_id:
            raise HTTPException(
                status_code=400,
                detail="Un contenedor no pertenece a esta operación",
            )
        db.add(OpeHblContenedor(
            hbl_id=h.id, contenedor_id=e.contenedor_id,
            piezas=e.piezas, peso_kg=e.peso_kg, cbm=e.cbm,
        ))


def _sincronizar_cargos(db: Session, h: OpeHbl, cargos) -> None:
    db.query(OpeBlCargo).filter(OpeBlCargo.hbl_id == h.id).delete()
    for i, c in enumerate(cargos or [], start=1):
        db.add(OpeBlCargo(
            hbl_id=h.id, orden=c.orden or i, concepto=c.concepto,
            tarifa=c.tarifa, unidad=c.unidad, moneda=c.moneda,
            valor=c.valor, pago=c.pago,
        ))


def crear_hbl(db: Session, operacion_id: uuid.UUID, data: HblCreate, actor: UsuarioActual) -> HblResponse:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    actor_id = uuid.UUID(actor.id)

    if data.mbl_id:
        mbl = db.query(OpeMbl).filter(OpeMbl.id == data.mbl_id, OpeMbl.operacion_id == op.id).first()
        if not mbl:
            raise HTTPException(status_code=400, detail="El MBL no pertenece a esta operación")
    if data.cotizacion_id:
        cot = db.query(OpeCotizacion).filter(
            OpeCotizacion.id == data.cotizacion_id, OpeCotizacion.operacion_id == op.id).first()
        if not cot:
            raise HTTPException(status_code=400, detail="La cotización no pertenece a esta operación")

    h = OpeHbl(operacion_id=op.id, numero_hbl=data.numero_hbl, creado_por=actor_id)
    _aplicar(h, data, _CAMPOS_BL + ["mbl_id", "cotizacion_id", "origen", "emisor_id",
                                    "emisor_texto", "do_numero", "consignee_a_la_orden",
                                    "agente_entrega"], False)
    # Lo recibido del agente ya viene emitido: no tiene sentido dejarlo en borrador.
    h.estado = "EMITIDA" if h.origen == "RECIBIDO" else "BORRADOR"
    db.add(h)
    db.flush()
    _sincronizar_contenedores(db, h, data.contenedores)
    _sincronizar_cargos(db, h, data.cargos)
    audit(db, "ope_hbl", h.id, "INSERT", actor_id,
          contexto={"operacion": op.numero, "numero_hbl": h.numero_hbl, "origen": h.origen})
    db.commit()
    db.refresh(h)
    return _hbl_resp(db, h)


def actualizar_hbl(db: Session, operacion_id: uuid.UUID, hbl_id: uuid.UUID,
                   data: HblUpdate, actor: UsuarioActual) -> HblResponse:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    h = db.query(OpeHbl).filter(OpeHbl.id == hbl_id, OpeHbl.operacion_id == op.id).first()
    if not h:
        raise HTTPException(status_code=404, detail="HBL no encontrado")
    if h.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="Un HBL anulado no se puede modificar")
    # Un HBL propio ya emitido es un documento entregado: solo se corrige anulando.
    if h.estado == "EMITIDA" and h.origen == "EMITIDO":
        raise HTTPException(
            status_code=400,
            detail="El HBL ya fue emitido. Para corregirlo hay que anularlo y emitir uno nuevo.",
        )

    _aplicar(h, data, _CAMPOS_BL + ["numero_hbl", "mbl_id", "cotizacion_id", "origen",
                                    "emisor_id", "emisor_texto", "do_numero",
                                    "consignee_a_la_orden", "agente_entrega"], True)
    if data.contenedores is not None:
        _sincronizar_contenedores(db, h, data.contenedores)
    if data.cargos is not None:
        _sincronizar_cargos(db, h, data.cargos)
    h.modificado_por = uuid.UUID(actor.id)
    h.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(h)
    return _hbl_resp(db, h)


def emitir_hbl(db: Session, operacion_id: uuid.UUID, hbl_id: uuid.UUID, actor: UsuarioActual) -> HblResponse:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    h = db.query(OpeHbl).filter(OpeHbl.id == hbl_id, OpeHbl.operacion_id == op.id).first()
    if not h:
        raise HTTPException(status_code=404, detail="HBL no encontrado")
    if h.estado != "BORRADOR":
        raise HTTPException(status_code=400, detail=f"Solo se emite un HBL en BORRADOR. Estado: {h.estado}")
    if not h.contenedores:
        raise HTTPException(status_code=400, detail="No se puede emitir un HBL sin contenedores")
    actor_id = uuid.UUID(actor.id)
    h.estado = "EMITIDA"
    h.emitido_por = actor_id
    h.emitido_en = datetime.now(timezone.utc)
    audit(db, "ope_hbl", h.id, "UPDATE", actor_id,
          campo="estado", valor_anterior="BORRADOR", valor_nuevo="EMITIDA",
          contexto={"numero_hbl": h.numero_hbl})
    db.commit()
    db.refresh(h)
    return _hbl_resp(db, h)


def anular_hbl(db: Session, operacion_id: uuid.UUID, hbl_id: uuid.UUID,
               motivo: str, actor: UsuarioActual) -> HblResponse:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    h = db.query(OpeHbl).filter(OpeHbl.id == hbl_id, OpeHbl.operacion_id == op.id).first()
    if not h:
        raise HTTPException(status_code=404, detail="HBL no encontrado")
    if h.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="El HBL ya está anulado")
    actor_id = uuid.UUID(actor.id)
    estado_anterior = h.estado
    h.estado = "ANULADA"
    h.anulado_por = actor_id
    h.anulado_en = datetime.now(timezone.utc)
    h.anulado_motivo = motivo
    audit(db, "ope_hbl", h.id, "UPDATE", actor_id,
          campo="estado", valor_anterior=estado_anterior, valor_nuevo="ANULADA",
          contexto={"numero_hbl": h.numero_hbl, "motivo": motivo})
    db.commit()
    db.refresh(h)
    return _hbl_resp(db, h)


def eliminar_hbl(db: Session, operacion_id: uuid.UUID, hbl_id: uuid.UUID, actor: UsuarioActual) -> None:
    op = _operacion(db, operacion_id)
    _verificar_editable(op)
    h = db.query(OpeHbl).filter(OpeHbl.id == hbl_id, OpeHbl.operacion_id == op.id).first()
    if not h:
        raise HTTPException(status_code=404, detail="HBL no encontrado")
    if h.estado == "EMITIDA":
        raise HTTPException(
            status_code=400,
            detail="Un HBL emitido no se borra: se anula, para que quede el rastro.",
        )
    db.delete(h)
    db.commit()


# ---------------------------------------------------------------------------
# Búsqueda / tracking
# ---------------------------------------------------------------------------

def buscar(db: Session, q: str, limite: int = 30) -> list[MaritimoBusquedaItem]:
    """Busca por número de BL, booking o contenedor.

    Es la consulta del día a día: hacen seguimiento dos o tres veces por semana
    y los clientes también preguntan por su propio número.
    """
    if not q or not q.strip():
        return []
    term = f"%{q.strip().upper()}%"
    resultados: list[MaritimoBusquedaItem] = []
    vistos: set = set()

    def agregar(op: OpeOperacion, coincide_por: str, valor: str, documento: str,
                buque=None, viaje=None, etd=None, eta=None, arribo=None):
        clave = (op.id, documento, valor)
        if clave in vistos:
            return
        vistos.add(clave)
        clientes = []
        for c in op.cotizaciones:
            if not c.activo:
                continue
            n = _nombre(db, c.cliente_id)
            if n and n not in clientes:
                clientes.append(n)
        resultados.append(MaritimoBusquedaItem(
            operacion_id=op.id, operacion_numero=op.numero, operacion_estado=op.estado,
            coincide_por=coincide_por, valor=valor, documento=documento,
            buque=buque, viaje=viaje, etd=etd, eta=eta, fecha_arribo=arribo,
            clientes=clientes,
        ))

    t = q.strip().upper()

    def por_donde(campos: list[tuple[str, str | None]]) -> str:
        """Qué campo hizo la coincidencia, para que el resultado lo explique."""
        for etiqueta, valor in campos:
            if valor and t in valor.upper():
                return etiqueta
        return "BL"

    for m in db.query(OpeMbl).filter(
        or_(OpeMbl.numero_bl.ilike(term), OpeMbl.booking_no.ilike(term))
    ).limit(limite).all():
        if m.operacion:
            agregar(m.operacion, por_donde([("BL", m.numero_bl), ("BOOKING", m.booking_no)]),
                    m.numero_bl, "MBL", m.buque, m.viaje, m.etd, m.eta, m.fecha_arribo)

    for h in db.query(OpeHbl).filter(
        or_(OpeHbl.numero_hbl.ilike(term), OpeHbl.booking_no.ilike(term),
            OpeHbl.do_numero.ilike(term), OpeHbl.referencia_cliente.ilike(term))
    ).limit(limite).all():
        if h.operacion:
            agregar(h.operacion,
                    por_donde([("BL", h.numero_hbl), ("BOOKING", h.booking_no),
                               ("DO", h.do_numero), ("REF. CLIENTE", h.referencia_cliente)]),
                    h.numero_hbl, "HBL", h.buque, h.viaje, h.etd, h.eta, h.fecha_arribo)

    for c in db.query(OpeContenedor).filter(
        OpeContenedor.numero.ilike(term)
    ).limit(limite).all():
        if c.operacion:
            mbl = db.get(OpeMbl, c.mbl_id) if c.mbl_id else None
            agregar(c.operacion, "CONTENEDOR", c.numero, "CONTENEDOR",
                    mbl.buque if mbl else None, mbl.viaje if mbl else None,
                    mbl.etd if mbl else None, mbl.eta if mbl else None,
                    mbl.fecha_arribo if mbl else None)

    return resultados[:limite]
