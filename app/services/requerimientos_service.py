import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.models.req import ReqRequerimiento, ReqMensaje
from app.models.admin import AdmUsuario
from app.schemas.auth import UsuarioActual
from app.schemas.requerimientos import (
    RequerimientoCreate, RequerimientoEstadoRequest, MensajeCreate,
    RequerimientoListItem, RequerimientoResponse, RequerimientoListResponse,
    MensajeResponse,
)

MAX_ADJUNTO_BYTES = 5 * 1024 * 1024  # 5 MB


def _nombre(db: Session, uid) -> str | None:
    if not uid:
        return None
    u = db.get(AdmUsuario, uid)
    return f"{u.nombre} {u.apellido}" if u else None


def _generar_numero(db: Session) -> str:
    from datetime import date as _date
    anio = datetime.now(timezone.utc).year
    prefijo = f"REQ-{anio}"
    ultimo = (
        db.query(ReqRequerimiento)
        .filter(ReqRequerimiento.numero.like(f"{prefijo}%"))
        .order_by(ReqRequerimiento.numero.desc())
        .first()
    )
    consecutivo = int(ultimo.numero[-4:]) + 1 if ultimo else 1
    return f"{prefijo}{consecutivo:04d}"


def _list_item(db: Session, r: ReqRequerimiento) -> RequerimientoListItem:
    return RequerimientoListItem(
        id=r.id, numero=r.numero, asunto=r.asunto, estado=r.estado, prioridad=r.prioridad,
        fecha_limite=r.fecha_limite,
        solicitante_id=r.solicitante_id, solicitante_nombre=_nombre(db, r.solicitante_id),
        asignado_id=r.asignado_id, asignado_nombre=_nombre(db, r.asignado_id),
        tiene_adjunto=bool(r.archivo_ruta), creado_en=r.creado_en,
    )


def _msg_response(db: Session, m: ReqMensaje) -> MensajeResponse:
    return MensajeResponse(
        id=m.id, usuario_id=m.usuario_id, usuario_nombre=_nombre(db, m.usuario_id),
        tipo=m.tipo, cuerpo=m.cuerpo, estado_nuevo=m.estado_nuevo, creado_en=m.creado_en,
    )


def _detalle(db: Session, r: ReqRequerimiento) -> RequerimientoResponse:
    base = _list_item(db, r).model_dump()
    msgs = sorted(r.mensajes, key=lambda x: x.creado_en)
    return RequerimientoResponse(
        **base, descripcion=r.descripcion, archivo_nombre=r.archivo_nombre,
        mensajes=[_msg_response(db, m) for m in msgs],
    )


def listar_usuarios_seleccionables(db: Session):
    from app.schemas.requerimientos import UsuarioSeleccion
    rows = db.query(AdmUsuario).filter(AdmUsuario.activo == True).order_by(AdmUsuario.nombre).all()
    return [UsuarioSeleccion(id=u.id, nombre=f"{u.nombre} {u.apellido}", email=u.email) for u in rows]


def obtener(db: Session, req_id: uuid.UUID) -> ReqRequerimiento:
    r = db.query(ReqRequerimiento).filter(
        ReqRequerimiento.id == req_id, ReqRequerimiento.activo == True
    ).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requerimiento no encontrado")
    return r


def listar(
    db: Session, actor: UsuarioActual, buzon: str = "recibidos",
    estado: str | None = None, prioridad: str | None = None,
    remitente_id: uuid.UUID | None = None,
    fecha_desde: str | None = None, fecha_hasta: str | None = None,
    no_finalizados: bool = False, pagina: int = 1, por_pagina: int = 50,
) -> RequerimientoListResponse:
    uid = uuid.UUID(actor.id)
    q = db.query(ReqRequerimiento).filter(ReqRequerimiento.activo == True)
    if buzon == "enviados":
        q = q.filter(ReqRequerimiento.solicitante_id == uid)
    else:
        q = q.filter(ReqRequerimiento.asignado_id == uid)
    if estado:
        q = q.filter(ReqRequerimiento.estado == estado)
    if no_finalizados:
        q = q.filter(ReqRequerimiento.estado != "REALIZADO")
    if prioridad:
        q = q.filter(ReqRequerimiento.prioridad == prioridad)
    if remitente_id:
        q = q.filter(ReqRequerimiento.solicitante_id == remitente_id)
    if fecha_desde:
        q = q.filter(ReqRequerimiento.creado_en >= fecha_desde)
    if fecha_hasta:
        q = q.filter(ReqRequerimiento.creado_en <= f"{fecha_hasta} 23:59:59")
    total = q.count()
    rows = (
        q.order_by(ReqRequerimiento.creado_en.desc())
        .offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    )
    return RequerimientoListResponse(
        items=[_list_item(db, r) for r in rows], total=total, pagina=pagina, por_pagina=por_pagina,
    )


def pendientes_count(db: Session, actor: UsuarioActual) -> int:
    uid = uuid.UUID(actor.id)
    return (
        db.query(ReqRequerimiento)
        .filter(
            ReqRequerimiento.activo == True,
            ReqRequerimiento.asignado_id == uid,
            ReqRequerimiento.estado != "REALIZADO",
        ).count()
    )


def obtener_detalle(db: Session, req_id: uuid.UUID) -> RequerimientoResponse:
    return _detalle(db, obtener(db, req_id))


def crear(db: Session, data: RequerimientoCreate, actor: UsuarioActual) -> RequerimientoResponse:
    if str(data.asignado_id) == str(actor.id):
        raise HTTPException(status_code=400, detail="No puedes dirigirte un requerimiento a ti mismo")
    if not db.get(AdmUsuario, data.asignado_id):
        raise HTTPException(status_code=400, detail="El usuario asignado no existe")
    r = ReqRequerimiento(
        numero=_generar_numero(db),
        asunto=data.asunto,
        descripcion=data.descripcion,
        solicitante_id=uuid.UUID(actor.id),
        asignado_id=data.asignado_id,
        estado="PENDIENTE",
        prioridad=data.prioridad,
        fecha_limite=data.fecha_limite,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _detalle(db, r)


def cambiar_estado(db: Session, req_id: uuid.UUID, data: RequerimientoEstadoRequest, actor: UsuarioActual) -> RequerimientoResponse:
    r = obtener(db, req_id)
    if data.estado == r.estado:
        return _detalle(db, r)
    anterior = r.estado
    r.estado = data.estado
    r.modificado_por = uuid.UUID(actor.id)
    r.modificado_en = datetime.now(timezone.utc)
    db.add(ReqMensaje(
        requerimiento_id=r.id, usuario_id=uuid.UUID(actor.id),
        tipo="CAMBIO_ESTADO", estado_nuevo=data.estado,
        cuerpo=f"Cambió el estado de {anterior} a {data.estado}",
    ))
    db.commit()
    db.refresh(r)
    return _detalle(db, r)


def agregar_mensaje(db: Session, req_id: uuid.UUID, data: MensajeCreate, actor: UsuarioActual) -> RequerimientoResponse:
    r = obtener(db, req_id)
    if not data.cuerpo.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
    db.add(ReqMensaje(
        requerimiento_id=r.id, usuario_id=uuid.UUID(actor.id),
        tipo="COMENTARIO", cuerpo=data.cuerpo.strip(),
    ))
    db.commit()
    db.refresh(r)
    return _detalle(db, r)


def subir_adjunto(db: Session, req_id: uuid.UUID, archivo: UploadFile, actor: UsuarioActual) -> RequerimientoResponse:
    from app.services import adjuntos_service
    r = obtener(db, req_id)
    contenido = archivo.file.read()
    if len(contenido) > MAX_ADJUNTO_BYTES:
        raise HTTPException(status_code=400, detail="El archivo supera el límite de 5 MB")

    # Registro unificado en adm_adjunto (uno por requerimiento).
    a = adjuntos_service.crear(
        db, "req_requerimiento", r.id, archivo.filename or "archivo",
        contenido, archivo.content_type, uuid.UUID(actor.id), reemplazar_unico=True,
    )
    r.archivo_nombre = a.nombre_archivo
    r.archivo_ruta = str(a.id)  # puntero al adjunto unificado
    r.modificado_por = uuid.UUID(actor.id)
    r.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    return _detalle(db, r)


def descargar_adjunto(db: Session, req_id: uuid.UUID):
    from app.core.config import settings
    from app.core import almacenamiento
    from app.models.adjuntos import AdmAdjunto
    r = obtener(db, req_id)
    if not r.archivo_ruta:
        raise HTTPException(status_code=404, detail="Sin adjunto")
    adj = None
    try:
        adj = db.get(AdmAdjunto, uuid.UUID(str(r.archivo_ruta)))
    except (ValueError, AttributeError):
        adj = None
    if adj:
        key, nombre = adj.storage_key, adj.nombre_archivo
    else:
        key, nombre = r.archivo_ruta, (r.archivo_nombre or Path(r.archivo_ruta).name)  # legacy
    ruta = settings.upload_path / str(key).replace("\\", "/")
    if ruta.exists():
        return FileResponse(path=str(ruta), filename=nombre)
    try:
        data = almacenamiento.leer(key)
    except Exception:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return StreamingResponse(iter([data]), media_type="application/octet-stream",
                             headers={"Content-Disposition": f'attachment; filename="{nombre}"'})
