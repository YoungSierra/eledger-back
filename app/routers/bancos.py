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
    MovimientosBancoResponse,
    TransferenciaCreate, TransferenciaResponse, TransferenciaListItem,
    ExtractoCreate, ExtractoLineaCreate, ConciliarRequest, DesconciliarRequest,
)
from app.schemas.facturacion import PreviewAsientoResponse
from app.services import bancos_service, transferencias_service, conciliacion_service
from fastapi import UploadFile, File
from pydantic import BaseModel


class _AnularReq(BaseModel):
    motivo: str = ""

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


@router.get("/cuentas/{id}/movimientos", response_model=MovimientosBancoResponse)
def movimientos_cuenta(
    id: uuid.UUID,
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.movimientos_cuenta(db, id, fecha_desde, fecha_hasta)


@router.get("/cuentas/{id}/movimientos/excel")
def movimientos_excel(
    id: uuid.UUID,
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return bancos_service.movimientos_excel(db, id, fecha_desde, fecha_hasta)


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


# ─── Transferencias entre cuentas ────────────────────────────────────────────

@router.get("/transferencias", response_model=list[TransferenciaListItem])
def listar_transferencias(
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return transferencias_service.listar(db, fecha_desde, fecha_hasta)


@router.post("/transferencias", response_model=TransferenciaResponse, status_code=201)
def crear_transferencia(
    body: TransferenciaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return transferencias_service.crear(db, body, actor)


@router.get("/transferencias/{id}", response_model=TransferenciaResponse)
def obtener_transferencia(
    id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return transferencias_service.obtener(db, id)


@router.get("/transferencias/{id}/asiento", response_model=PreviewAsientoResponse)
def asiento_transferencia(
    id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return transferencias_service.asiento(db, id)


@router.put("/transferencias/{id}", response_model=TransferenciaResponse)
def actualizar_transferencia(
    id: uuid.UUID, body: TransferenciaCreate,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return transferencias_service.actualizar(db, id, body, actor)


@router.post("/transferencias/{id}/contabilizar", response_model=TransferenciaResponse)
def contabilizar_transferencia(
    id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return transferencias_service.contabilizar(db, id, actor)


@router.post("/transferencias/{id}/anular", response_model=TransferenciaResponse)
def anular_transferencia(
    id: uuid.UUID, body: _AnularReq,
    db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user),
):
    return transferencias_service.anular(db, id, body.motivo, actor)


# ─── Conciliación bancaria ───────────────────────────────────────────────────

@router.get("/extractos")
def listar_extractos(cuenta_id: uuid.UUID | None = Query(None), db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.listar_extractos(db, cuenta_id)


@router.post("/extractos", status_code=201)
def crear_extracto(body: ExtractoCreate, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.crear_extracto(db, body, actor)


@router.get("/extractos/{id}")
def obtener_extracto(id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.obtener_extracto(db, id)


@router.delete("/extractos/{id}")
def eliminar_extracto(id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.eliminar_extracto(db, id, actor)


@router.get("/extractos/{id}/libro")
def libro_extracto(id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.libro_no_conciliado(db, id)


@router.post("/extractos/{id}/lineas")
def agregar_linea(id: uuid.UUID, body: ExtractoLineaCreate, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.agregar_linea(db, id, body, actor)


@router.post("/extractos/{id}/importar")
async def importar_extracto(id: uuid.UUID, archivo: UploadFile = File(...), db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    contenido = await archivo.read()
    return conciliacion_service.importar_csv(db, id, contenido, actor)


@router.delete("/extractos/lineas/{linea_id}")
def eliminar_linea(linea_id: uuid.UUID, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.eliminar_linea(db, linea_id, actor)


@router.post("/extractos/conciliar")
def conciliar(body: ConciliarRequest, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.conciliar(db, body.extracto_linea_id, body.asiento_linea_id, actor)


@router.post("/extractos/desconciliar")
def desconciliar(body: DesconciliarRequest, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.desconciliar(db, body.extracto_linea_id, actor)


@router.post("/extractos/{id}/estado")
def cambiar_estado_extracto(id: uuid.UUID, body: dict, db: Session = Depends(get_db), actor: UsuarioActual = Depends(get_current_user)):
    return conciliacion_service.cambiar_estado(db, id, body.get("estado"), actor)
