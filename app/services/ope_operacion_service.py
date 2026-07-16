import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.ope import (
    OpeOperacion, OpeHawb, OpeMawb,
    OpeManifiesto, OpeManifiestoLinea,
    OpeEvento, OpeDocumento,
)
from app.schemas.auth import UsuarioActual
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
    return op


def obtener_operacion_por_cotizacion(db: Session, cotizacion_id: uuid.UUID) -> OpeOperacion:
    op = db.query(OpeOperacion).filter(OpeOperacion.cotizacion_id == cotizacion_id).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La cotización no tiene operación asociada")
    return op


def listar_operaciones(
    db: Session,
    actor: UsuarioActual,
    estado: str | None = None,
    busqueda: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> list[OpeOperacion]:
    from app.models.ope import OpeCotizacion
    q = db.query(OpeOperacion).filter(OpeOperacion.activo == True)
    if actor.ver_solo_propios:
        q = q.join(OpeCotizacion, OpeOperacion.cotizacion_id == OpeCotizacion.id)\
             .filter(OpeCotizacion.asesor_id == uuid.UUID(actor.id))
    if estado:
        q = q.filter(OpeOperacion.estado == estado)
    if busqueda:
        q = q.filter(OpeOperacion.numero.ilike(f"%{busqueda}%"))
    if fecha_desde:
        q = q.filter(OpeOperacion.fecha_apertura >= fecha_desde)
    if fecha_hasta:
        q = q.filter(OpeOperacion.fecha_apertura <= fecha_hasta)
    return q.order_by(OpeOperacion.fecha_apertura.desc(), OpeOperacion.creado_en.desc()).all()


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
    cot = obtener_cotizacion(db, op.cotizacion_id)
    return OpeOperacionCarpetaResponse(
        operacion=op,
        cotizacion=cot,
        hawbs=op.hawbs,
        mawbs=op.mawbs,
        manifiestos=op.manifiestos,
        eventos=op.eventos,
        documentos=op.documentos,
    )


# ---------------------------------------------------------------------------
# HAWB
# ---------------------------------------------------------------------------

def listar_hawbs(db: Session, operacion_id: uuid.UUID) -> list[OpeHawb]:
    obtener_operacion(db, operacion_id)
    return db.query(OpeHawb).filter(OpeHawb.operacion_id == operacion_id).order_by(OpeHawb.creado_en).all()


def obtener_hawb(db: Session, operacion_id: uuid.UUID, hawb_id: uuid.UUID) -> OpeHawb:
    h = db.query(OpeHawb).filter(OpeHawb.id == hawb_id, OpeHawb.operacion_id == operacion_id).first()
    if not h:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HAWB no encontrado")
    return h


def crear_hawb(db: Session, operacion_id: uuid.UUID, data: OpeHawbCreate, actor: UsuarioActual) -> OpeHawb:
    op = obtener_operacion(db, operacion_id)
    if op.estado == "CERRADA":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una operación cerrada")
    h = OpeHawb(
        operacion_id=operacion_id,
        creado_por=uuid.UUID(actor.id),
        **data.model_dump(),
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def actualizar_hawb(
    db: Session, operacion_id: uuid.UUID, hawb_id: uuid.UUID, data: OpeHawbUpdate, actor: UsuarioActual
) -> OpeHawb:
    h = obtener_hawb(db, operacion_id, hawb_id)
    if h.estado == "ANULADA":
        raise HTTPException(status_code=400, detail="No se puede modificar un HAWB anulado")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(h, campo, valor)
    h.modificado_por = uuid.UUID(actor.id)
    h.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(h)
    return h


# ---------------------------------------------------------------------------
# MAWB
# ---------------------------------------------------------------------------

def listar_mawbs(db: Session, operacion_id: uuid.UUID) -> list[OpeMawb]:
    obtener_operacion(db, operacion_id)
    return db.query(OpeMawb).filter(OpeMawb.operacion_id == operacion_id).order_by(OpeMawb.creado_en).all()


def obtener_mawb(db: Session, operacion_id: uuid.UUID, mawb_id: uuid.UUID) -> OpeMawb:
    m = db.query(OpeMawb).filter(OpeMawb.id == mawb_id, OpeMawb.operacion_id == operacion_id).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAWB no encontrado")
    return m


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


# ---------------------------------------------------------------------------
# Manifiesto
# ---------------------------------------------------------------------------

def obtener_manifiesto(db: Session, operacion_id: uuid.UUID, manifiesto_id: uuid.UUID) -> OpeManifiesto:
    m = db.query(OpeManifiesto).filter(
        OpeManifiesto.id == manifiesto_id, OpeManifiesto.operacion_id == operacion_id
    ).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifiesto no encontrado")
    return m


def listar_manifiestos(db: Session, operacion_id: uuid.UUID) -> list[OpeManifiesto]:
    obtener_operacion(db, operacion_id)
    return db.query(OpeManifiesto).filter(OpeManifiesto.operacion_id == operacion_id).order_by(OpeManifiesto.fecha).all()


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


# ---------------------------------------------------------------------------
# Eventos (bitácora)
# ---------------------------------------------------------------------------

def listar_eventos(db: Session, operacion_id: uuid.UUID) -> list[OpeEvento]:
    obtener_operacion(db, operacion_id)
    return (
        db.query(OpeEvento)
        .filter(OpeEvento.operacion_id == operacion_id)
        .order_by(OpeEvento.fecha_hora.desc())
        .all()
    )


def registrar_evento(
    db: Session, operacion_id: uuid.UUID, data: OpeEventoCreate, actor: UsuarioActual
) -> OpeEvento:
    obtener_operacion(db, operacion_id)
    evento = OpeEvento(
        operacion_id=operacion_id,
        usuario_id=uuid.UUID(actor.id),
        tipo=data.tipo,
        descripcion=data.descripcion,
        notificado_cliente=data.notificado_cliente,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


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
