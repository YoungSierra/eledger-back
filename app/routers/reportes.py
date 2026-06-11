from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.services import reportes_service

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.get("/mayor")
def mayor(
    cuenta_desde: str = Query(...),
    cuenta_hasta: str = Query(...),
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    tercero_id: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.libro_mayor(db, cuenta_desde, cuenta_hasta, fecha_desde, fecha_hasta, tercero_id)


@router.get("/mayor/excel")
def mayor_excel(
    cuenta_desde: str = Query(...),
    cuenta_hasta: str = Query(...),
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    tercero_id: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.libro_mayor_excel(db, cuenta_desde, cuenta_hasta, fecha_desde, fecha_hasta, tercero_id)


@router.get("/auxiliar")
def auxiliar(
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    cuenta_desde: str | None = Query(None),
    cuenta_hasta: str | None = Query(None),
    tercero_id: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.auxiliar_tercero(db, cuenta_desde, cuenta_hasta, fecha_desde, fecha_hasta, tercero_id)


@router.get("/auxiliar/excel")
def auxiliar_excel(
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    cuenta_desde: str | None = Query(None),
    cuenta_hasta: str | None = Query(None),
    tercero_id: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.auxiliar_excel(db, cuenta_desde, cuenta_hasta, fecha_desde, fecha_hasta, tercero_id)


@router.get("/resultados")
def resultados(
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    nivel: int = Query(3, ge=1, le=9),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.estado_resultados(db, fecha_desde, fecha_hasta, nivel)


@router.get("/resultados/excel")
def resultados_excel(
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    nivel: int = Query(3, ge=1, le=9),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.resultados_excel(db, fecha_desde, fecha_hasta, nivel)


@router.get("/balance")
def balance(
    fecha_corte: date = Query(...),
    nivel: int = Query(3, ge=1, le=9),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.balance_general(db, fecha_corte, nivel)


@router.get("/balance/excel")
def balance_excel(
    fecha_corte: date = Query(...),
    nivel: int = Query(3, ge=1, le=9),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.balance_excel(db, fecha_corte, nivel)


@router.get("/balanza")
def balanza(
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    nivel: int = Query(3, ge=1, le=9),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.balanza_comprobacion(db, fecha_desde, fecha_hasta, nivel)


@router.get("/balanza/excel")
def balanza_excel(
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    nivel: int = Query(3, ge=1, le=9),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return reportes_service.balanza_excel(db, fecha_desde, fecha_hasta, nivel)
