import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.admin import AdmConsecutivo, AdmTipoDocumento
from app.schemas.auth import UsuarioActual
from app.schemas.consecutivos import ConsecutivoCreate, ConsecutivoUpdate, ConsecutivoResponse

MODULO_ORDEN = ["administracion", "contabilidad", "facturacion", "cxc", "cxp", "compras", "bancos"]

# Códigos sembrados por el sistema — no se pueden eliminar
CODIGOS_SISTEMA = {"AM", "ANU", "AJU", "DEP", "NOM", "ANT", "ANTP", "COT", "CP", "FAC", "FCP", "NCC", "NDB", "OC", "REC", "RECP", "RM", "AJ", "TR"}


def _ejemplo(obj: AdmConsecutivo) -> str:
    siguiente = obj.numero_actual + 1
    num = str(siguiente).zfill(obj.longitud_minima)
    return f"{obj.prefijo or ''}{num}"


def _to_response(obj: AdmConsecutivo) -> ConsecutivoResponse:
    td = obj.tipo_documento
    return ConsecutivoResponse(
        id=obj.id,
        tipo_documento_id=obj.tipo_documento_id,
        tipo_documento_codigo=td.codigo,
        tipo_documento_nombre=td.nombre,
        tipo_documento_modulo=td.modulo,
        prefijo=obj.prefijo,
        numero_actual=obj.numero_actual,
        numero_inicio=obj.numero_inicio,
        longitud_minima=obj.longitud_minima,
        ejemplo=_ejemplo(obj),
        activo=obj.activo,
        es_personalizado=td.codigo not in CODIGOS_SISTEMA,
    )


def crear_consecutivo(db: Session, data: ConsecutivoCreate, actor: UsuarioActual) -> ConsecutivoResponse:
    codigo = data.codigo.strip().upper()
    if codigo in CODIGOS_SISTEMA:
        raise HTTPException(status_code=400, detail="Ese código está reservado por el sistema")
    if db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe un tipo de documento con ese código")
    td = AdmTipoDocumento(
        codigo=codigo,
        nombre=data.nombre.strip(),
        modulo="contabilidad",
        activo=True,
    )
    db.add(td)
    db.flush()
    obj = AdmConsecutivo(
        tipo_documento_id=td.id,
        prefijo=data.prefijo.strip().upper() if data.prefijo else None,
        numero_actual=0,
        numero_inicio=data.numero_inicio,
        longitud_minima=data.longitud_minima,
        activo=True,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_response(obj)


def eliminar_consecutivo(db: Session, id: uuid.UUID) -> None:
    obj = db.query(AdmConsecutivo).filter(AdmConsecutivo.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Consecutivo no encontrado")
    td = obj.tipo_documento
    if td.codigo in CODIGOS_SISTEMA:
        raise HTTPException(status_code=400, detail="No se pueden eliminar consecutivos del sistema")
    if obj.numero_actual > 0:
        raise HTTPException(status_code=400, detail="No se puede eliminar — ya tiene documentos generados")
    db.delete(obj)
    db.delete(td)
    db.commit()


def listar_consecutivos(db: Session) -> list[ConsecutivoResponse]:
    rows = (
        db.query(AdmConsecutivo)
        .join(AdmTipoDocumento)
        .order_by(AdmTipoDocumento.modulo, AdmTipoDocumento.codigo)
        .all()
    )
    return [_to_response(r) for r in rows]


def actualizar_consecutivo(
    db: Session, id: uuid.UUID, data: ConsecutivoUpdate, actor: UsuarioActual
) -> ConsecutivoResponse:
    obj = db.query(AdmConsecutivo).filter(AdmConsecutivo.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Consecutivo no encontrado")
    if obj.numero_actual > 0 and data.numero_inicio is not None:
        raise HTTPException(
            status_code=400,
            detail="No se puede cambiar el número de inicio después de haber generado documentos"
        )
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return _to_response(obj)
