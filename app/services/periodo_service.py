import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.contabilidad import CntPeriodo, CntPeriodoReapertura
from app.schemas.auth import UsuarioActual
from app.schemas.periodos import PeriodoCreate, PeriodoUpdate


def listar_periodos(db: Session, anio: int | None = None) -> list[CntPeriodo]:
    q = db.query(CntPeriodo).filter(CntPeriodo.activo == True)
    if anio:
        q = q.filter(CntPeriodo.anio == anio)
    return q.order_by(CntPeriodo.anio.desc(), CntPeriodo.mes.desc()).all()


def obtener_periodo(db: Session, periodo_id: uuid.UUID) -> CntPeriodo:
    p = db.query(CntPeriodo).filter(CntPeriodo.id == periodo_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Período no encontrado")
    return p


def crear_periodo(db: Session, data: PeriodoCreate, actor: UsuarioActual) -> CntPeriodo:
    periodo = CntPeriodo(
        anio=data.anio,
        mes=data.mes,
        fecha_inicio=data.fecha_inicio,
        fecha_cierre=data.fecha_cierre,
        estado="abierto",
        creado_por=actor.id,
    )
    db.add(periodo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un período para {data.anio}/{data.mes:02d}",
        )
    db.refresh(periodo)
    return periodo


def actualizar_periodo(db: Session, periodo_id: uuid.UUID, data: PeriodoUpdate, actor: UsuarioActual) -> CntPeriodo:
    p = obtener_periodo(db, periodo_id)
    if p.estado != "abierto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden editar fechas de períodos en estado 'abierto'",
        )
    p.fecha_inicio = data.fecha_inicio
    p.fecha_cierre = data.fecha_cierre
    p.modificado_por = actor.id
    p.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return p


def cerrar_periodo(db: Session, periodo_id: uuid.UUID, actor: UsuarioActual) -> CntPeriodo:
    p = obtener_periodo(db, periodo_id)

    if p.estado != "abierto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden cerrar períodos en estado 'abierto'. Estado actual: '{p.estado}'",
        )

    p.estado = "cerrado"
    p.cerrado_en = datetime.now(timezone.utc)
    p.cerrado_por = actor.id
    p.modificado_por = actor.id
    p.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(p)
    return p


def reabrir_periodo(db: Session, periodo_id: uuid.UUID, motivo: str, actor: UsuarioActual) -> CntPeriodo:
    p = obtener_periodo(db, periodo_id)

    if p.estado == "abierto":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El período ya está abierto",
        )
    if p.estado == "bloqueado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El período está bloqueado y no puede reabrirse sin autorización especial",
        )

    reapertura = CntPeriodoReapertura(
        periodo_id=p.id,
        estado_anterior=p.estado,
        motivo=motivo,
        autorizado_por=actor.id,
    )
    db.add(reapertura)

    p.estado = "abierto"
    p.modificado_por = actor.id
    p.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(p)
    return p
