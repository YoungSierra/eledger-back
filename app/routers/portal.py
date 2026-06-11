"""
Portal de cliente — endpoints de solo lectura filtrados por tercero_id del usuario.
Solo accesible para usuarios cuyo rol tiene es_cliente=True.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.admin import AdmUsuario, AdmRol
from app.models.adm import AdmTercero
from app.models.ope import OpeOperacion, OpeEvento, OpeHawb, OpeMawb, OpeCotizacion
from app.schemas.auth import UsuarioActual

router = APIRouter(prefix="/portal", tags=["Portal cliente"])


# ── Guard: solo usuarios cliente ─────────────────────────────────────────────

def get_cliente_actual(
    actor: UsuarioActual = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdmUsuario:
    usuario = db.query(AdmUsuario).filter(AdmUsuario.id == uuid.UUID(actor.id)).first()
    if not usuario or not usuario.tercero_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso exclusivo para usuarios cliente")
    rol = db.query(AdmRol).filter(AdmRol.id == usuario.rol_id).first()
    if not rol or not rol.es_cliente:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso exclusivo para usuarios cliente")
    return usuario


# ── Schemas ───────────────────────────────────────────────────────────────────

class EventoPortal(BaseModel):
    fecha_hora: str
    tipo: str
    descripcion: str
    notificado_cliente: bool


class HawbPortal(BaseModel):
    numero_hawb: str
    vuelo: Optional[str]
    fecha_vuelo: Optional[str]
    piezas: Optional[int]
    peso_cargable_kg: Optional[Decimal]
    estado: str


class MawbPortal(BaseModel):
    numero_mawb: str
    vuelo: Optional[str]
    fecha_vuelo: Optional[str]
    estado: str


class OperacionPortal(BaseModel):
    id: str
    numero: str
    fecha_apertura: str
    estado: str
    origen: str
    destino: str
    tipo_operacion: str
    ultimo_evento: Optional[str]
    ultima_fecha: Optional[str]
    piezas: Optional[int]
    peso_kg: Optional[Decimal]
    hawbs_count: int
    mawbs_count: int


class OperacionDetallePortal(BaseModel):
    id: str
    numero: str
    fecha_apertura: str
    estado: str
    origen: str
    destino: str
    tipo_operacion: str
    piezas: Optional[int]
    peso_kg: Optional[Decimal]
    hawbs: list[HawbPortal]
    mawbs: list[MawbPortal]
    eventos: list[EventoPortal]


# ── Helpers ───────────────────────────────────────────────────────────────────

PROGRESO = {"ABIERTA": 1, "EN_CURSO": 2, "CERRADA": 3, "CANCELADA": 0}

TIPO_EVENTO_LABEL = {
    "STATUS":             "Estado actualizado",
    "DOCUMENTO_RECIBIDO": "Documento recibido",
    "NOTA":               "Nota",
    "RESERVA":            "Reserva confirmada",
    "APERTURA":           "Operación abierta",
    "CIERRE":             "Operación cerrada",
}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/me")
def portal_me(usuario: AdmUsuario = Depends(get_cliente_actual), db: Session = Depends(get_db)):
    tercero = db.query(AdmTercero).filter(AdmTercero.id == usuario.tercero_id).first()
    return {
        "nombre": f"{usuario.nombre} {usuario.apellido}",
        "email": usuario.email,
        "cliente": tercero.razon_social if tercero else "",
        "nit": tercero.nit if tercero else "",
    }


@router.get("/operaciones", response_model=list[OperacionPortal])
def listar_operaciones(
    usuario: AdmUsuario = Depends(get_cliente_actual),
    db: Session = Depends(get_db),
):


    operaciones = (
        db.query(OpeOperacion)
        .join(OpeCotizacion, OpeOperacion.cotizacion_id == OpeCotizacion.id)
        .filter(OpeCotizacion.cliente_id == usuario.tercero_id)
        .order_by(OpeOperacion.fecha_apertura.desc())
        .all()
    )

    resultado = []
    for op in operaciones:
        eventos = (
            db.query(OpeEvento)
            .filter(OpeEvento.operacion_id == op.id, OpeEvento.notificado_cliente == True)
            .order_by(OpeEvento.fecha_hora.desc())
            .first()
        )
        hawbs_count = db.query(OpeHawb).filter(OpeHawb.operacion_id == op.id).count()
        mawbs_count = db.query(OpeMawb).filter(OpeMawb.operacion_id == op.id).count()

        resultado.append(OperacionPortal(
            id=str(op.id),
            numero=op.numero,
            fecha_apertura=op.fecha_apertura.isoformat(),
            estado=op.estado,
            origen=op.cotizacion.origen if op.cotizacion else "",
            destino=op.cotizacion.destino if op.cotizacion else "",
            tipo_operacion=op.cotizacion.tipo_operacion if op.cotizacion else "",
            ultimo_evento=eventos.descripcion if eventos else None,
            ultima_fecha=eventos.fecha_hora.strftime("%Y-%m-%d %H:%M") if eventos else None,
            piezas=op.piezas,
            peso_kg=op.peso_kg,
            hawbs_count=hawbs_count,
            mawbs_count=mawbs_count,
        ))
    return resultado


@router.get("/operaciones/{operacion_id}", response_model=OperacionDetallePortal)
def detalle_operacion(
    operacion_id: uuid.UUID,
    usuario: AdmUsuario = Depends(get_cliente_actual),
    db: Session = Depends(get_db),
):


    op = (
        db.query(OpeOperacion)
        .join(OpeCotizacion, OpeOperacion.cotizacion_id == OpeCotizacion.id)
        .filter(OpeOperacion.id == operacion_id, OpeCotizacion.cliente_id == usuario.tercero_id)
        .first()
    )
    if not op:
        raise HTTPException(status_code=404, detail="Operación no encontrada")

    hawbs = db.query(OpeHawb).filter(OpeHawb.operacion_id == op.id).all()
    mawbs = db.query(OpeMawb).filter(OpeMawb.operacion_id == op.id).all()
    eventos = (
        db.query(OpeEvento)
        .filter(OpeEvento.operacion_id == op.id, OpeEvento.notificado_cliente == True)
        .order_by(OpeEvento.fecha_hora.desc())
        .all()
    )

    return OperacionDetallePortal(
        id=str(op.id),
        numero=op.numero,
        fecha_apertura=op.fecha_apertura.isoformat(),
        estado=op.estado,
        origen=op.cotizacion.origen if op.cotizacion else "",
        destino=op.cotizacion.destino if op.cotizacion else "",
        tipo_operacion=op.cotizacion.tipo_operacion if op.cotizacion else "",
        piezas=op.piezas,
        peso_kg=op.peso_kg,
        hawbs=[HawbPortal(
            numero_hawb=h.numero_hawb,
            vuelo=h.vuelo,
            fecha_vuelo=h.fecha_vuelo.isoformat() if h.fecha_vuelo else None,
            piezas=h.piezas,
            peso_cargable_kg=h.peso_cargable_kg,
            estado=h.estado,
        ) for h in hawbs],
        mawbs=[MawbPortal(
            numero_mawb=m.numero_mawb,
            vuelo=m.vuelo,
            fecha_vuelo=m.fecha_vuelo.isoformat() if m.fecha_vuelo else None,
            estado=m.estado,
        ) for m in mawbs],
        eventos=[EventoPortal(
            fecha_hora=e.fecha_hora.strftime("%Y-%m-%d %H:%M"),
            tipo=TIPO_EVENTO_LABEL.get(e.tipo, e.tipo),
            descripcion=e.descripcion,
            notificado_cliente=e.notificado_cliente,
        ) for e in eventos],
    )
