import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.ope import (
    OpeOperacion, OpeCotizacion, OpeHawb, OpeMawb,
    OpeManifiesto, OpeManifiestoLinea,
    OpeEvento, OpeDocumento,
)
from app.models.admin import AdmUsuario
from app.models.adm import AdmTercero
from app.schemas.auth import UsuarioActual


def _nombre_usuario(db: Session, uid) -> str | None:
    if not uid:
        return None
    u = db.get(AdmUsuario, uid)
    return f"{u.nombre} {u.apellido}" if u else None


def _attach_audit(db: Session, obj):
    """Adjunta los nombres de quién emitió/anuló para la respuesta."""
    if obj is not None:
        obj.emitido_por_nombre = _nombre_usuario(db, getattr(obj, "emitido_por", None))
        obj.anulado_por_nombre = _nombre_usuario(db, getattr(obj, "anulado_por", None))
        # HAWB: resolver cotización/cliente al que pertenece la guía.
        if hasattr(obj, "numero_hawb"):
            cot = db.get(OpeCotizacion, obj.cotizacion_id) if obj.cotizacion_id else None
            obj.cotizacion_numero = cot.numero if cot else None
            cli = db.get(AdmTercero, cot.cliente_id) if cot else None
            obj.cliente_nombre = cli.razon_social if cli else None
    return obj


def _clientes_de_operacion(db: Session, op: OpeOperacion) -> list[dict]:
    """Clientes involucrados en la operación (distintos, desde sus cotizaciones)."""
    vistos: dict = {}
    for c in op.cotizaciones:
        if c.cliente_id in vistos:
            continue
        t = db.get(AdmTercero, c.cliente_id)
        vistos[c.cliente_id] = {"id": c.cliente_id, "nombre": t.razon_social if t else "", "nit": t.nit if t else None}
    return list(vistos.values())


def _attach_operacion(db: Session, op: OpeOperacion) -> OpeOperacion:
    op.clientes = _clientes_de_operacion(db, op)
    return op


def _attach_evento(db: Session, e: OpeEvento) -> OpeEvento:
    h = db.get(OpeHawb, e.hawb_id) if e.hawb_id else None
    e.hawb_numero = h.numero_hawb if h else None
    return e
from app.schemas.ope import (
    OpeOperacionUpdate,
    OpeHawbCreate, OpeHawbUpdate,
    OpeMawbCreate, OpeMawbUpdate,
    OpeManifiestoCreate, OpeManifiestoUpdate,
    OpeEventoCreate,
    OpeDocumentoCreate, OpeDocumentoUpdate,
    OpeOperacionCarpetaResponse,
)


# ---------------------------------------------------------------------------
# Operación
# ---------------------------------------------------------------------------

def obtener_operacion(db: Session, operacion_id: uuid.UUID) -> OpeOperacion:
    op = db.query(OpeOperacion).filter(
        OpeOperacion.id == operacion_id,
        OpeOperacion.activo == True,
    ).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operación no encontrada")
    return _attach_operacion(db, op)


def obtener_operacion_por_cotizacion(db: Session, cotizacion_id: uuid.UUID) -> OpeOperacion:
    cot = db.get(OpeCotizacion, cotizacion_id)
    if not cot or not cot.operacion_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La cotización no tiene operación asociada")
    return obtener_operacion(db, cot.operacion_id)


def listar_operaciones(
    db: Session,
    actor: UsuarioActual,
    estado: str | None = None,
    busqueda: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> list[OpeOperacion]:
    q = db.query(OpeOperacion).filter(OpeOperacion.activo == True)
    if actor.ver_solo_propios:
        q = q.join(OpeCotizacion, OpeCotizacion.operacion_id == OpeOperacion.id)\
             .filter(OpeCotizacion.asesor_id == uuid.UUID(actor.id))\
             .distinct()
    if estado:
        q = q.filter(OpeOperacion.estado == estado)
    if busqueda:
        q = q.filter(OpeOperacion.numero.ilike(f"%{busqueda}%"))
    if fecha_desde:
        q = q.filter(OpeOperacion.fecha_apertura >= fecha_desde)
    if fecha_hasta:
        q = q.filter(OpeOperacion.fecha_apertura <= fecha_hasta)
    rows = q.order_by(OpeOperacion.fecha_apertura.desc(), OpeOperacion.creado_en.desc()).all()
    for op in rows:
        _attach_operacion(db, op)
    return rows


def actualizar_operacion(
    db: Session, operacion_id: uuid.UUID, data: OpeOperacionUpdate, actor: UsuarioActual
) -> OpeOperacion:
    op = obtener_operacion(db, operacion_id)
    if op.estado == "CERRADA":
        raise HTTPException(status_code=400, detail="No se puede modificar una operación cerrada")

    # Validación de cierre: no se puede cerrar con MAWB/HAWB en borrador.
    # Deben estar emitidos (o anulados) antes de cerrar la operación.
    if data.estado == "CERRADA":
        mawb_borr = db.query(OpeMawb).filter(
            OpeMawb.operacion_id == op.id, OpeMawb.estado == "BORRADOR"
        ).count()
        hawb_borr = db.query(OpeHawb).filter(
            OpeHawb.operacion_id == op.id, OpeHawb.estado == "BORRADOR"
        ).count()
        manif_borr = db.query(OpeManifiesto).filter(
            OpeManifiesto.operacion_id == op.id, OpeManifiesto.estado == "BORRADOR"
        ).count()
        pendientes = []
        if mawb_borr:
            pendientes.append(f"{mawb_borr} MAWB")
        if hawb_borr:
            pendientes.append(f"{hawb_borr} HAWB")
        if manif_borr:
            pendientes.append(f"{manif_borr} manifiesto(s)")
        if pendientes:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede cerrar la operación: hay {' y '.join(pendientes)} en borrador. "
                       "Deben estar emitidos o anulados antes de cerrar.",
            )

    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(op, campo, valor)
    op.modificado_por = uuid.UUID(actor.id)
    op.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(op)
    return op


def obtener_carpeta(db: Session, operacion_id: uuid.UUID) -> OpeOperacionCarpetaResponse:
    op = obtener_operacion(db, operacion_id)
    from app.services.ope_cotizacion_service import obtener_cotizacion
    cotizaciones = [obtener_cotizacion(db, c.id) for c in
                    sorted(op.cotizaciones, key=lambda x: x.numero)]
    for h in op.hawbs:
        _attach_audit(db, h)
    for m in op.mawbs:
        _attach_audit(db, m)
    for mf in op.manifiestos:
        _attach_audit(db, mf)
    eventos = [_attach_evento(db, e) for e in op.eventos]
    return OpeOperacionCarpetaResponse(
        operacion=op,
        cotizaciones=cotizaciones,
        clientes=op.clientes,
        hawbs=op.hawbs,
        mawbs=op.mawbs,
        manifiestos=op.manifiestos,
        eventos=eventos,
        documentos=op.documentos,
    )


# ---------------------------------------------------------------------------
# HAWB
# ---------------------------------------------------------------------------

def listar_hawbs(db: Session, operacion_id: uuid.UUID) -> list[OpeHawb]:
    obtener_operacion(db, operacion_id)
    rows = db.query(OpeHawb).filter(OpeHawb.operacion_id == operacion_id).order_by(OpeHawb.creado_en).all()
    for r in rows:
        _attach_audit(db, r)
    return rows


def obtener_hawb(db: Session, operacion_id: uuid.UUID, hawb_id: uuid.UUID) -> OpeHawb:
    h = db.query(OpeHawb).filter(OpeHawb.id == hawb_id, OpeHawb.operacion_id == operacion_id).first()
    if not h:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HAWB no encontrado")
    return _attach_audit(db, h)


def _validar_cotizacion_op(db: Session, operacion_id: uuid.UUID, cotizacion_id) -> None:
    if not cotizacion_id:
        return
    cot = db.get(OpeCotizacion, cotizacion_id)
    if not cot or cot.operacion_id != operacion_id:
        raise HTTPException(status_code=400, detail="La cotización seleccionada no pertenece a esta operación")


def crear_hawb(db: Session, operacion_id: uuid.UUID, data: OpeHawbCreate, actor: UsuarioActual) -> OpeHawb:
    op = obtener_operacion(db, operacion_id)
    if op.estado == "CERRADA":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una operación cerrada")
    _validar_cotizacion_op(db, operacion_id, data.cotizacion_id)
    h = OpeHawb(
        operacion_id=operacion_id,
        creado_por=uuid.UUID(actor.id),
        **data.model_dump(),
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return _attach_audit(db, h)


def actualizar_hawb(
    db: Session, operacion_id: uuid.UUID, hawb_id: uuid.UUID, data: OpeHawbUpdate, actor: UsuarioActual
) -> OpeHawb:
    h = obtener_hawb(db, operacion_id, hawb_id)
    if h.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="No se puede modificar un HAWB anulado")
    _validar_cotizacion_op(db, operacion_id, data.cotizacion_id)
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(h, campo, valor)
    h.modificado_por = uuid.UUID(actor.id)
    h.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(h)
    return _attach_audit(db, h)


def emitir_hawb(db: Session, operacion_id: uuid.UUID, hawb_id: uuid.UUID, actor: UsuarioActual) -> OpeHawb:
    h = obtener_hawb(db, operacion_id, hawb_id)
    if h.estado != "BORRADOR":
        raise HTTPException(status_code=400, detail="Solo se puede emitir un HAWB en borrador")
    if not h.cotizacion_id:
        raise HTTPException(status_code=400, detail="Asigna la cotización/cliente al HAWB antes de emitirlo")
    h.estado = "EMITIDA"
    h.emitido_por = uuid.UUID(actor.id)
    h.emitido_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(h)
    return _attach_audit(db, h)


def anular_hawb(db: Session, operacion_id: uuid.UUID, hawb_id: uuid.UUID, motivo: str, actor: UsuarioActual) -> OpeHawb:
    h = obtener_hawb(db, operacion_id, hawb_id)
    if h.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="El HAWB ya está anulado")
    h.estado = "ANULADA"
    h.anulado_por = uuid.UUID(actor.id)
    h.anulado_en = datetime.now(timezone.utc)
    h.anulado_motivo = motivo
    db.commit()
    db.refresh(h)
    return _attach_audit(db, h)


# ---------------------------------------------------------------------------
# MAWB
# ---------------------------------------------------------------------------

def listar_mawbs(db: Session, operacion_id: uuid.UUID) -> list[OpeMawb]:
    obtener_operacion(db, operacion_id)
    rows = db.query(OpeMawb).filter(OpeMawb.operacion_id == operacion_id).order_by(OpeMawb.creado_en).all()
    for r in rows:
        _attach_audit(db, r)
    return rows


def obtener_mawb(db: Session, operacion_id: uuid.UUID, mawb_id: uuid.UUID) -> OpeMawb:
    m = db.query(OpeMawb).filter(OpeMawb.id == mawb_id, OpeMawb.operacion_id == operacion_id).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAWB no encontrado")
    return _attach_audit(db, m)


def crear_mawb(db: Session, operacion_id: uuid.UUID, data: OpeMawbCreate, actor: UsuarioActual) -> OpeMawb:
    op = obtener_operacion(db, operacion_id)
    if op.estado == "CERRADA":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una operación cerrada")
    m = OpeMawb(
        operacion_id=operacion_id,
        creado_por=uuid.UUID(actor.id),
        **data.model_dump(),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def actualizar_mawb(
    db: Session, operacion_id: uuid.UUID, mawb_id: uuid.UUID, data: OpeMawbUpdate, actor: UsuarioActual
) -> OpeMawb:
    m = obtener_mawb(db, operacion_id, mawb_id)
    if m.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="No se puede modificar un MAWB anulado")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(m, campo, valor)
    m.modificado_por = uuid.UUID(actor.id)
    m.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return m


def emitir_mawb(db: Session, operacion_id: uuid.UUID, mawb_id: uuid.UUID, actor: UsuarioActual) -> OpeMawb:
    m = obtener_mawb(db, operacion_id, mawb_id)
    if m.estado != "BORRADOR":
        raise HTTPException(status_code=400, detail="Solo se puede emitir un MAWB en borrador")
    m.estado = "EMITIDA"
    m.emitido_por = uuid.UUID(actor.id)
    m.emitido_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return _attach_audit(db, m)


def anular_mawb(db: Session, operacion_id: uuid.UUID, mawb_id: uuid.UUID, motivo: str, actor: UsuarioActual) -> OpeMawb:
    m = obtener_mawb(db, operacion_id, mawb_id)
    if m.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="El MAWB ya está anulado")
    m.estado = "ANULADA"
    m.anulado_por = uuid.UUID(actor.id)
    m.anulado_en = datetime.now(timezone.utc)
    m.anulado_motivo = motivo
    db.commit()
    db.refresh(m)
    return _attach_audit(db, m)


# ---------------------------------------------------------------------------
# Manifiesto
# ---------------------------------------------------------------------------

def obtener_manifiesto(db: Session, operacion_id: uuid.UUID, manifiesto_id: uuid.UUID) -> OpeManifiesto:
    m = db.query(OpeManifiesto).filter(
        OpeManifiesto.id == manifiesto_id, OpeManifiesto.operacion_id == operacion_id
    ).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifiesto no encontrado")
    return _attach_audit(db, m)


def listar_manifiestos(db: Session, operacion_id: uuid.UUID) -> list[OpeManifiesto]:
    obtener_operacion(db, operacion_id)
    rows = db.query(OpeManifiesto).filter(OpeManifiesto.operacion_id == operacion_id).order_by(OpeManifiesto.fecha).all()
    for r in rows:
        _attach_audit(db, r)
    return rows


def crear_manifiesto(db: Session, operacion_id: uuid.UUID, data: OpeManifiestoCreate, actor: UsuarioActual) -> OpeManifiesto:
    op = obtener_operacion(db, operacion_id)
    if op.estado == "CERRADA":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una operación cerrada")

    mawb = db.query(OpeMawb).filter(OpeMawb.id == data.mawb_id, OpeMawb.operacion_id == operacion_id).first()
    if not mawb:
        raise HTTPException(status_code=400, detail="El MAWB no pertenece a esta operación")

    actor_id = uuid.UUID(actor.id)
    manifiesto = OpeManifiesto(
        operacion_id=operacion_id,
        mawb_id=data.mawb_id,
        aerolinea_id=data.aerolinea_id,
        fecha=data.fecha,
        creado_por=actor_id,
    )
    db.add(manifiesto)
    db.flush()

    for linea_data in data.lineas:
        linea = OpeManifiestoLinea(
            manifiesto_id=manifiesto.id,
            hawb_id=linea_data.hawb_id,
            exportador_id=linea_data.exportador_id,
            importador_id=linea_data.importador_id,
            piezas=linea_data.piezas,
            peso_kg=linea_data.peso_kg,
            descripcion=linea_data.descripcion,
        )
        db.add(linea)

    db.commit()
    db.refresh(manifiesto)
    return manifiesto


def actualizar_manifiesto(
    db: Session, operacion_id: uuid.UUID, manifiesto_id: uuid.UUID,
    data: OpeManifiestoUpdate, actor: UsuarioActual,
) -> OpeManifiesto:
    op = obtener_operacion(db, operacion_id)
    if op.estado == "CERRADA":
        raise HTTPException(status_code=400, detail="No se puede modificar una operación cerrada")
    m = db.query(OpeManifiesto).filter(
        OpeManifiesto.id == manifiesto_id, OpeManifiesto.operacion_id == operacion_id
    ).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifiesto no encontrado")
    if m.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="No se puede modificar un manifiesto anulado")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(m, campo, valor)
    db.commit()
    db.refresh(m)
    return m


def emitir_manifiesto(db: Session, operacion_id: uuid.UUID, manifiesto_id: uuid.UUID, actor: UsuarioActual) -> OpeManifiesto:
    m = obtener_manifiesto(db, operacion_id, manifiesto_id)
    if m.estado != "BORRADOR":
        raise HTTPException(status_code=400, detail="Solo se puede emitir un manifiesto en borrador")
    m.estado = "EMITIDA"
    m.emitido_por = uuid.UUID(actor.id)
    m.emitido_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return _attach_audit(db, m)


def anular_manifiesto(db: Session, operacion_id: uuid.UUID, manifiesto_id: uuid.UUID, motivo: str, actor: UsuarioActual) -> OpeManifiesto:
    m = obtener_manifiesto(db, operacion_id, manifiesto_id)
    if m.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="El manifiesto ya está anulado")
    m.estado = "ANULADA"
    m.anulado_por = uuid.UUID(actor.id)
    m.anulado_en = datetime.now(timezone.utc)
    m.anulado_motivo = motivo
    db.commit()
    db.refresh(m)
    return _attach_audit(db, m)


# ---------------------------------------------------------------------------
# Eventos (bitácora)
# ---------------------------------------------------------------------------

def listar_eventos(db: Session, operacion_id: uuid.UUID) -> list[OpeEvento]:
    obtener_operacion(db, operacion_id)
    rows = (
        db.query(OpeEvento)
        .filter(OpeEvento.operacion_id == operacion_id)
        .order_by(OpeEvento.fecha_hora.desc())
        .all()
    )
    for e in rows:
        _attach_evento(db, e)
    return rows


def registrar_evento(
    db: Session, operacion_id: uuid.UUID, data: OpeEventoCreate, actor: UsuarioActual
) -> OpeEvento:
    obtener_operacion(db, operacion_id)
    if data.hawb_id:
        h = db.query(OpeHawb).filter(OpeHawb.id == data.hawb_id, OpeHawb.operacion_id == operacion_id).first()
        if not h:
            raise HTTPException(status_code=400, detail="El HAWB no pertenece a esta operación")
    evento = OpeEvento(
        operacion_id=operacion_id,
        hawb_id=data.hawb_id,
        usuario_id=uuid.UUID(actor.id),
        tipo=data.tipo,
        descripcion=data.descripcion,
        notificado_cliente=data.notificado_cliente,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return _attach_evento(db, evento)


# ---------------------------------------------------------------------------
# Documentos requeridos
# ---------------------------------------------------------------------------

def listar_documentos(db: Session, operacion_id: uuid.UUID) -> list[OpeDocumento]:
    obtener_operacion(db, operacion_id)
    return db.query(OpeDocumento).filter(OpeDocumento.operacion_id == operacion_id).order_by(OpeDocumento.tipo).all()


def crear_documento(
    db: Session, operacion_id: uuid.UUID, data: OpeDocumentoCreate, actor: UsuarioActual
) -> OpeDocumento:
    obtener_operacion(db, operacion_id)
    doc = OpeDocumento(
        operacion_id=operacion_id,
        tipo=data.tipo,
        nombre=data.nombre,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def actualizar_documento(
    db: Session, operacion_id: uuid.UUID, documento_id: uuid.UUID,
    data: OpeDocumentoUpdate, actor: UsuarioActual,
) -> OpeDocumento:
    doc = db.query(OpeDocumento).filter(
        OpeDocumento.id == documento_id, OpeDocumento.operacion_id == operacion_id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(doc, campo, valor)
    db.commit()
    db.refresh(doc)
    return doc


def subir_archivo(
    db: Session, operacion_id: uuid.UUID, documento_id: uuid.UUID,
    archivo: UploadFile, upload_path: Path, actor: UsuarioActual,
) -> OpeDocumento:
    doc = db.query(OpeDocumento).filter(
        OpeDocumento.id == documento_id, OpeDocumento.operacion_id == operacion_id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")

    # Carpeta por operación
    carpeta = upload_path / str(operacion_id)
    carpeta.mkdir(parents=True, exist_ok=True)

    suffix = Path(archivo.filename or "").suffix.lower()
    nombre_archivo = f"{documento_id}{suffix}"
    ruta = carpeta / nombre_archivo

    with open(ruta, "wb") as f:
        f.write(archivo.file.read())

    doc.archivo = str(Path(str(operacion_id)) / nombre_archivo)
    db.commit()
    db.refresh(doc)
    return doc


def descargar_archivo(
    db: Session, operacion_id: uuid.UUID, documento_id: uuid.UUID,
) -> FileResponse:
    from app.core.config import settings
    doc = db.query(OpeDocumento).filter(
        OpeDocumento.id == documento_id, OpeDocumento.operacion_id == operacion_id
    ).first()
    if not doc or not doc.archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    ruta = settings.upload_path / doc.archivo
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en disco")
    return FileResponse(path=str(ruta), filename=Path(doc.archivo).name)
