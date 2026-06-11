import json
import uuid
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permisos import require_permission
from app.models.admin import AdmMoneda, AdmModulo, AdmOpcion, AdmPermisoOpcion, AdmTrm
from app.schemas.auth import UsuarioActual

router = APIRouter(prefix="/trm", tags=["TRM"])

DATOS_GOV_URL = (
    "https://www.datos.gov.co/resource/32sa-8pi3.json"
    "?$limit=1&$order=vigenciadesde+DESC"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_o_crear_moneda(db: Session, codigo: str, nombre: str, simbolo: str, es_funcional: bool, actor_id: uuid.UUID) -> AdmMoneda:
    m = db.query(AdmMoneda).filter(AdmMoneda.codigo == codigo).first()
    if not m:
        m = AdmMoneda(codigo=codigo, nombre=nombre, simbolo=simbolo, decimales=2,
                      es_funcional=es_funcional, creado_por=actor_id)
        db.add(m)
        db.flush()
    return m


def _trm_hoy(db: Session) -> AdmTrm | None:
    hoy = date.today()
    return (
        db.query(AdmTrm)
        .filter(AdmTrm.fecha >= datetime(hoy.year, hoy.month, hoy.day))
        .filter(AdmTrm.fecha < datetime(hoy.year, hoy.month, hoy.day, 23, 59, 59))
        .first()
    )


def _fetch_sugerida() -> Decimal | None:
    try:
        req = urllib.request.Request(DATOS_GOV_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data and "valor" in data[0]:
                return Decimal(str(data[0]["valor"]).replace(",", "."))
    except Exception:
        pass
    return None


def _puede_editar(db: Session, rol_id: str) -> bool:
    return bool(
        db.query(AdmPermisoOpcion)
        .join(AdmOpcion, AdmPermisoOpcion.opcion_id == AdmOpcion.id)
        .join(AdmModulo, AdmOpcion.modulo_id == AdmModulo.id)
        .filter(
            AdmPermisoOpcion.rol_id == uuid.UUID(rol_id),
            AdmModulo.codigo == "administracion",
            AdmModulo.activo == True,
            AdmOpcion.activo == True,
            AdmPermisoOpcion.puede_editar == True,
        )
        .first()
    )


# ── Schemas ───────────────────────────────────────────────────────────────────

class TrmHoyResponse(BaseModel):
    existe: bool
    fecha: str
    tasa: Decimal | None
    sugerida: Decimal | None
    puede_editar: bool


class TrmCreate(BaseModel):
    tasa: Decimal
    fecha: str | None = None  # YYYY-MM-DD, si None usa hoy


class TrmResponse(BaseModel):
    id: str
    fecha: str
    tasa: Decimal
    fuente: str | None

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TrmResponse])
def listar_trm(
    limite: int = 90,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "ver")),
):
    registros = (
        db.query(AdmTrm)
        .order_by(AdmTrm.fecha.desc())
        .limit(limite)
        .all()
    )
    return [
        TrmResponse(
            id=str(r.id),
            fecha=r.fecha.date().isoformat(),
            tasa=r.tasa,
            fuente=r.fuente,
        )
        for r in registros
    ]


@router.get("/hoy", response_model=TrmHoyResponse)
def trm_hoy(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    registro = _trm_hoy(db)
    puede = _puede_editar(db, actor.rol_id)
    sugerida = None if registro else _fetch_sugerida()

    return TrmHoyResponse(
        existe=registro is not None,
        fecha=date.today().isoformat(),
        tasa=registro.tasa if registro else None,
        sugerida=sugerida,
        puede_editar=puede,
    )


@router.post("", response_model=TrmResponse, status_code=201)
def guardar_trm(
    body: TrmCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "editar")),
):
    fecha_dt = datetime.strptime(body.fecha, "%Y-%m-%d") if body.fecha else datetime.combine(date.today(), datetime.min.time())

    # Asegurar que USD y COP existan
    actor_uid = uuid.UUID(actor.id)
    usd = _get_o_crear_moneda(db, "USD", "Dólar estadounidense", "$", False, actor_uid)
    cop = _get_o_crear_moneda(db, "COP", "Peso colombiano", "$", True, actor_uid)

    # Upsert: si ya existe para esa fecha, actualiza
    registro = (
        db.query(AdmTrm)
        .filter(
            AdmTrm.moneda_origen_id == usd.id,
            AdmTrm.moneda_destino_id == cop.id,
            AdmTrm.fecha >= datetime(fecha_dt.year, fecha_dt.month, fecha_dt.day),
            AdmTrm.fecha < datetime(fecha_dt.year, fecha_dt.month, fecha_dt.day, 23, 59, 59),
        )
        .first()
    )

    if registro:
        registro.tasa = body.tasa
        registro.fuente = "MANUAL"
    else:
        registro = AdmTrm(
            moneda_origen_id=usd.id,
            moneda_destino_id=cop.id,
            fecha=fecha_dt,
            tasa=body.tasa,
            fuente="MANUAL",
            creado_por=actor_uid,
        )
        db.add(registro)

    db.commit()
    db.refresh(registro)

    return TrmResponse(
        id=str(registro.id),
        fecha=registro.fecha.date().isoformat(),
        tasa=registro.tasa,
        fuente=registro.fuente,
    )
