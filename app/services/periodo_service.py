import calendar
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.admin import AdmConfiguracion
from app.models.contabilidad import CntPeriodo, CntPeriodoReapertura
from app.schemas.auth import UsuarioActual
from app.schemas.periodos import PeriodoCreate, PeriodoUpdate


def _cierre_automatico(db: Session) -> bool:
    """Lee el parámetro global periodo_cierre_automatico."""
    cfg = (
        db.query(AdmConfiguracion)
        .filter(AdmConfiguracion.clave == "periodo_cierre_automatico")
        .first()
    )
    return cfg is not None and cfg.valor == "true"


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
    # Un período de un mes que aún no ha llegado se crea "bloqueado" (programado):
    # no acepta transacciones hasta que se inicie manualmente. El mes vigente o
    # meses pasados nacen "abierto". Se compara por (año, mes) para evitar
    # problemas de zona horaria en los límites de mes.
    hoy = date.today()
    es_futuro = (data.anio, data.mes) > (hoy.year, hoy.month)
    periodo = CntPeriodo(
        anio=data.anio,
        mes=data.mes,
        fecha_inicio=data.fecha_inicio,
        fecha_cierre=data.fecha_cierre,
        estado="bloqueado" if es_futuro else "abierto",
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


def generar_anio(db: Session, anio: int, actor: UsuarioActual) -> list[CntPeriodo]:
    """Crea los 12 meses del año que aún no existan, todos en estado 'bloqueado'
    (programados / por abrir). Respeta los períodos ya creados. Devuelve la lista
    completa del año tras la generación."""
    existentes = {
        p.mes
        for p in db.query(CntPeriodo.mes).filter(CntPeriodo.anio == anio).all()
    }
    for mes in range(1, 13):
        if mes in existentes:
            continue
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        db.add(
            CntPeriodo(
                anio=anio,
                mes=mes,
                fecha_inicio=date(anio, mes, 1),
                fecha_cierre=date(anio, mes, ultimo_dia),
                estado="bloqueado",
                creado_por=actor.id,
            )
        )
    db.commit()
    return (
        db.query(CntPeriodo)
        .filter(CntPeriodo.anio == anio, CntPeriodo.activo == True)
        .order_by(CntPeriodo.mes.desc())
        .all()
    )


def actualizar_periodo(db: Session, periodo_id: uuid.UUID, data: PeriodoUpdate, actor: UsuarioActual) -> CntPeriodo:
    p = obtener_periodo(db, periodo_id)
    if p.estado not in ("abierto", "bloqueado"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden editar fechas de períodos abiertos o programados",
        )
    p.fecha_inicio = data.fecha_inicio
    p.fecha_cierre = data.fecha_cierre
    p.modificado_por = actor.id
    p.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return p


def iniciar_periodo(db: Session, periodo_id: uuid.UUID, actor: UsuarioActual) -> CntPeriodo:
    """Activa un período programado (bloqueado → abierto).

    Si el parámetro global periodo_cierre_automatico está activo, cierra los
    períodos abiertos cronológicamente anteriores (práctica Grupo 3: un solo
    período abierto a la vez).
    """
    p = obtener_periodo(db, periodo_id)

    if p.estado != "bloqueado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se puede iniciar un período programado. Estado actual: '{p.estado}'",
        )

    if _cierre_automatico(db):
        anteriores = (
            db.query(CntPeriodo)
            .filter(CntPeriodo.estado == "abierto", CntPeriodo.activo == True)
            .all()
        )
        ahora = datetime.now(timezone.utc)
        for ant in anteriores:
            if (ant.anio, ant.mes) < (p.anio, p.mes):
                ant.estado = "cerrado"
                ant.cerrado_en = ahora
                ant.cerrado_por = actor.id
                ant.modificado_por = actor.id
                ant.modificado_en = ahora

    p.estado = "abierto"
    p.modificado_por = actor.id
    p.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(p)
    return p


def cerrar_periodo(db: Session, periodo_id: uuid.UUID, actor: UsuarioActual) -> CntPeriodo:
    p = obtener_periodo(db, periodo_id)

    if p.estado not in ("abierto", "bloqueado"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden cerrar períodos abiertos o programados. Estado actual: '{p.estado}'",
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
            detail="El período está programado; use 'Iniciar período' para activarlo, no reapertura",
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
