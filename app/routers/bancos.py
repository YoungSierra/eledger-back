import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.bancos import (
    BancoCreate, BancoUpdate, BancoResponse,
    CuentaBancariaCreate, CuentaBancariaUpdate, CuentaBancariaResponse,
    ChequerapCreate, ChequeraUpdate, ChequeraResponse,
)
from app.services import bancos_service

router = APIRouter(prefix="/bancos", tags=["Bancos"])


@router.get("/bancos", response_model=list[BancoResponse])
def listar_bancos(
    solo_activos: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.listar_bancos(db, solo_activos)


@router.post("/bancos", response_model=BancoResponse, status_code=201)
def crear_banco(
    body: BancoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.crear_banco(db, body, actor)


@router.put("/bancos/{id}", response_model=BancoResponse)
def actualizar_banco(
    id: uuid.UUID, body: BancoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.actualizar_banco(db, id, body, actor)


@router.get("/cuentas", response_model=list[CuentaBancariaResponse])
def listar_cuentas(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.listar_cuentas(db, solo_activas)


@router.post("/cuentas", response_model=CuentaBancariaResponse, status_code=201)
def crear_cuenta(
    body: CuentaBancariaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.crear_cuenta(db, body, actor)


@router.put("/cuentas/{id}", response_model=CuentaBancariaResponse)
def actualizar_cuenta(
    id: uuid.UUID, body: CuentaBancariaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.actualizar_cuenta(db, id, body, actor)


@router.get("/chequeras", response_model=list[ChequeraResponse])
def listar_chequeras(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.listar_chequeras(db, solo_activas)


@router.post("/chequeras", response_model=ChequeraResponse, status_code=201)
def crear_chequera(
    body: ChequerapCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.crear_chequera(db, body, actor)


@router.put("/chequeras/{id}", response_model=ChequeraResponse)
def actualizar_chequera(
    id: uuid.UUID, body: ChequeraUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.actualizar_chequera(db, id, body, actor)
