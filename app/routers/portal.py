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
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.moneda import a_funcional, moneda_funcional, trm_corte
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.admin import AdmUsuario, AdmRol
from app.models.adm import AdmTercero
from app.models.ope import OpeOperacion, OpeEvento, OpeHawb, OpeMawb, OpeCotizacion
from app.models.facturacion import FacFactura
from app.models.cxc import CxcDocumento
from app.models.admin import AdmMoneda
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
        .join(OpeCotizacion, OpeCotizacion.operacion_id == OpeOperacion.id)
        .filter(OpeCotizacion.cliente_id == usuario.tercero_id)
        .order_by(OpeOperacion.fecha_apertura.desc())
        .distinct()
        .all()
    )

    resultado = []
    for op in operaciones:
        # Solo las cotizaciones/HAWB del cliente dentro de esta operación.
        cotis = [c for c in op.cotizaciones if c.cliente_id == usuario.tercero_id]
        coti_ids = [c.id for c in cotis]
        cot0 = cotis[0] if cotis else None
        # Piezas/peso SOLO de las cotizaciones del cliente (la operación puede tener varios clientes)
        piezas_cli = sum((c.piezas or 0) for c in cotis) or None
        peso_cli = sum((c.peso_kg or Decimal("0")) for c in cotis) or None
        hawbs_cli = db.query(OpeHawb).filter(
            OpeHawb.operacion_id == op.id, OpeHawb.cotizacion_id.in_(coti_ids)
        ).all() if coti_ids else []
        hawb_ids = [h.id for h in hawbs_cli]

        evento = (
            db.query(OpeEvento)
            .filter(
                OpeEvento.operacion_id == op.id,
                OpeEvento.notificado_cliente == True,
                or_(OpeEvento.hawb_id.is_(None), OpeEvento.hawb_id.in_(hawb_ids)),
            )
            .order_by(OpeEvento.fecha_hora.desc())
            .first()
        )
        mawbs_count = db.query(OpeMawb).filter(OpeMawb.operacion_id == op.id).count()

        resultado.append(OperacionPortal(
            id=str(op.id),
            numero=op.numero,
            fecha_apertura=op.fecha_apertura.isoformat(),
            estado=op.estado,
            origen=cot0.origen if cot0 else "",
            destino=cot0.destino if cot0 else "",
            tipo_operacion=cot0.tipo_operacion if cot0 else "",
            ultimo_evento=evento.descripcion if evento else None,
            ultima_fecha=evento.fecha_hora.strftime("%Y-%m-%d %H:%M") if evento else None,
            piezas=piezas_cli,
            peso_kg=peso_cli,
            hawbs_count=len(hawbs_cli),
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
        .join(OpeCotizacion, OpeCotizacion.operacion_id == OpeOperacion.id)
        .filter(OpeOperacion.id == operacion_id, OpeCotizacion.cliente_id == usuario.tercero_id)
        .first()
    )
    if not op:
        raise HTTPException(status_code=404, detail="Operación no encontrada")

    cotis = [c for c in op.cotizaciones if c.cliente_id == usuario.tercero_id]
    coti_ids = [c.id for c in cotis]
    cot0 = cotis[0] if cotis else None
    piezas_cli = sum((c.piezas or 0) for c in cotis) or None
    peso_cli = sum((c.peso_kg or Decimal("0")) for c in cotis) or None
    hawbs = db.query(OpeHawb).filter(
        OpeHawb.operacion_id == op.id, OpeHawb.cotizacion_id.in_(coti_ids)
    ).all() if coti_ids else []
    hawb_ids = [h.id for h in hawbs]
    mawbs = db.query(OpeMawb).filter(OpeMawb.operacion_id == op.id).all()
    eventos = (
        db.query(OpeEvento)
        .filter(
            OpeEvento.operacion_id == op.id,
            OpeEvento.notificado_cliente == True,
            or_(OpeEvento.hawb_id.is_(None), OpeEvento.hawb_id.in_(hawb_ids)),
        )
        .order_by(OpeEvento.fecha_hora.desc())
        .all()
    )

    return OperacionDetallePortal(
        id=str(op.id),
        numero=op.numero,
        fecha_apertura=op.fecha_apertura.isoformat(),
        estado=op.estado,
        origen=cot0.origen if cot0 else "",
        destino=cot0.destino if cot0 else "",
        tipo_operacion=cot0.tipo_operacion if cot0 else "",
        piezas=piezas_cli,
        peso_kg=peso_cli,
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


# ── Facturas / cartera / perfil ──────────────────────────────────────────────

def _saldo_factura(db, fac):
    """Saldo pendiente de la factura desde el documento CxC generado al contabilizarla."""
    doc = db.query(CxcDocumento).filter(
        CxcDocumento.origen_modulo == "fac_factura",
        CxcDocumento.origen_id == fac.id,
        CxcDocumento.activo == True,
    ).first()
    return doc.saldo if doc else None


@router.get("/facturas")
def portal_facturas(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    usuario: AdmUsuario = Depends(get_cliente_actual),
    db: Session = Depends(get_db),
):
    q = db.query(FacFactura).filter(
        FacFactura.cliente_id == usuario.tercero_id, FacFactura.estado != "borrador"
    )
    if fecha_desde:
        q = q.filter(FacFactura.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(FacFactura.fecha <= fecha_hasta)
    facs = q.order_by(FacFactura.fecha.desc(), FacFactura.numero.desc()).all()
    hoy = date.today()
    out = []
    for f in facs:
        moneda = db.query(AdmMoneda).filter(AdmMoneda.id == f.moneda_id).first()
        saldo = _saldo_factura(db, f)
        if f.estado == "anulada":
            estado_pago = "anulada"
        elif saldo is not None and saldo <= 0:
            estado_pago = "pagada"
        else:
            estado_pago = "pendiente"
        dias = (f.fecha_vencimiento - hoy).days if f.fecha_vencimiento else None
        out.append({
            "id": str(f.id),
            "numero": f.numero,
            "fecha": f.fecha.isoformat(),
            "fecha_vencimiento": f.fecha_vencimiento.isoformat() if f.fecha_vencimiento else None,
            "moneda": moneda.codigo if moneda else "",
            "total": str(f.total),
            "saldo": str(saldo) if saldo is not None else str(f.total),
            "estado": f.estado,
            "estado_pago": estado_pago,
            "dias_vencimiento": dias,
        })
    return out


@router.get("/cartera")
def portal_cartera(usuario: AdmUsuario = Depends(get_cliente_actual), db: Session = Depends(get_db)):
    docs = db.query(CxcDocumento).filter(
        CxcDocumento.tercero_id == usuario.tercero_id,
        CxcDocumento.estado == "contabilizado",
        CxcDocumento.activo == True,
        CxcDocumento.saldo > 0,
    ).all()
    hoy = date.today()
    # Los totales se acumulan en moneda funcional: sumar dólares con pesos daría
    # un número sin significado. Ver `app/core/moneda.py`.
    func = moneda_funcional(db)
    moneda_func_id = func.id if func else None
    tasas = trm_corte(db, hoy)
    monedas = {m.id: m.codigo for m in db.query(AdmMoneda).all()}
    corriente = Decimal("0")
    vencido = Decimal("0")
    a_favor = Decimal("0")
    items = []
    for d in docs:
        saldo_func = a_funcional(d, tasas, moneda_func_id, d.saldo)
        if d.tipo in ("NOTA_CREDITO", "ANTICIPO"):
            a_favor += saldo_func
            continue
        vence = d.fecha_vencimiento
        dias = (hoy - vence).days if vence else 0
        if vence is None or vence >= hoy:
            corriente += saldo_func
        else:
            vencido += saldo_func
        items.append({
            "numero": d.numero, "tipo": d.tipo,
            "fecha": d.fecha.isoformat(),
            "fecha_vencimiento": vence.isoformat() if vence else None,
            # Cada documento se muestra en SU moneda; los totales van convertidos.
            "total": str(d.total), "saldo": str(d.saldo),
            "moneda": monedas.get(d.moneda_id),
            "saldo_funcional": str(saldo_func),
            "dias_vencimiento": (vence - hoy).days if vence else None,
        })
    items.sort(key=lambda x: (x["fecha_vencimiento"] or ""))
    total = corriente + vencido - a_favor
    return {
        "corriente": str(corriente), "vencido": str(vencido),
        "a_favor": str(a_favor), "total_adeudado": str(total),
        "items": items,
    }


class PerfilUpdate(BaseModel):
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    nombre_contacto: Optional[str] = None
    cargo_contacto: Optional[str] = None
    telefono_contacto: Optional[str] = None
    email_contacto: Optional[str] = None


@router.get("/perfil")
def portal_perfil(usuario: AdmUsuario = Depends(get_cliente_actual), db: Session = Depends(get_db)):
    t = db.query(AdmTercero).filter(AdmTercero.id == usuario.tercero_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {
        "razon_social": t.razon_social, "nit": t.nit,
        "email": t.email, "telefono": t.telefono, "direccion": t.direccion, "ciudad": t.ciudad,
        "nombre_contacto": t.nombre_contacto, "cargo_contacto": t.cargo_contacto,
        "telefono_contacto": t.telefono_contacto, "email_contacto": t.email_contacto,
        "usuario_nombre": f"{usuario.nombre} {usuario.apellido}", "usuario_email": usuario.email,
    }


@router.put("/perfil")
def portal_perfil_update(body: PerfilUpdate, usuario: AdmUsuario = Depends(get_cliente_actual), db: Session = Depends(get_db)):
    t = db.query(AdmTercero).filter(AdmTercero.id == usuario.tercero_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for campo in ("telefono", "direccion", "ciudad", "nombre_contacto", "cargo_contacto", "telefono_contacto", "email_contacto"):
        val = getattr(body, campo)
        if val is not None:
            setattr(t, campo, val)
    db.commit()
    return portal_perfil(usuario, db)
