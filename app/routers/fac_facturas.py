import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core import almacenamiento
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.facturacion import FacFactura
from app.schemas.auth import UsuarioActual
from app.schemas.facturacion import (
    FacFacturaCreate, FacFacturaUpdate, AnularFacturaRequest,
    LineaFacCreate, RetencionFacCreate,
    FacFacturaResponse, FacListResponse, FacturarCotizacionRequest,
    PreviewAsientoResponse,
)
from app.services import facturacion_service, emision_service

router = APIRouter(prefix="/facturacion/facturas", tags=["Facturas de venta"])


@router.post("/{id}/transmitir")
def transmitir_dian(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Transmite la factura al PTH para su emisión ante la DIAN.

    Si el PTH la valida, el XML firmado y el PDF quedan archivados en nuestro
    propio almacenamiento (obligación DIAN de conservarlos 5 años).
    """
    return emision_service.transmitir_factura(db, id, actor)


@router.post("/retenciones-sugeridas", response_model=list[RetencionFacCreate])
def retenciones_sugeridas(
    body: list[LineaFacCreate],
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Retenciones que corresponden a estas líneas según lo parametrizado en cada concepto.

    Las calcula el backend y no la pantalla para que la factura manual y la que
    nace de una cotización usen exactamente la misma regla.
    """
    return facturacion_service.calcular_retenciones(db, body)


@router.post("/{id}/archivar")
def archivar_dian(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Reintenta el archivado del XML/PDF de una factura ya validada."""
    return emision_service.reintentar_archivado(db, id)


@router.get("/{id}/dian/{tipo}")
def descargar_documento_dian(
    id: uuid.UUID,
    tipo: str,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    """Descarga el XML o el PDF archivado de la factura (copia propia, no del PTH)."""
    if tipo not in ("xml", "pdf"):
        raise HTTPException(status_code=400, detail="Tipo debe ser 'xml' o 'pdf'")
    fac = db.query(FacFactura).filter(FacFactura.id == id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    key = fac.xml_key if tipo == "xml" else fac.pdf_key
    if not key:
        raise HTTPException(status_code=404, detail=f"La factura no tiene {tipo.upper()} archivado")
    nombre = f"{fac.numero_dian or fac.numero}.{tipo}"
    url = almacenamiento.url_descarga(key, nombre=nombre)
    if url:
        return {"url": url, "directo": True}
    return StreamingResponse(
        iter([almacenamiento.leer(key)]),
        media_type="application/xml" if tipo == "xml" else "application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/preview-asiento", response_model=PreviewAsientoResponse)
def preview_asiento(
    body: FacFacturaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.preview_asiento(db, body)


@router.get("/{id}/asiento", response_model=PreviewAsientoResponse)
def asiento_contabilizado(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.asiento_contabilizado(db, id)


@router.get("", response_model=FacListResponse)
def listar(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    estado: str | None = Query(None),
    dian_estado: str | None = Query(None),
    cliente_id: uuid.UUID | None = Query(None),
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.listar(db, pagina, por_pagina, estado, dian_estado, cliente_id, fecha_desde, fecha_hasta)


@router.post("", response_model=FacFacturaResponse, status_code=201)
def crear(
    body: FacFacturaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.crear(db, body, actor)


@router.post("/desde-cotizacion/{cotizacion_id}", response_model=FacFacturaResponse, status_code=201)
def facturar_cotizacion(
    cotizacion_id: uuid.UUID,
    body: FacturarCotizacionRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.facturar_cotizacion(db, cotizacion_id, body, actor)


@router.get("/{id}", response_model=FacFacturaResponse)
def obtener(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.obtener(db, id)


@router.put("/{id}", response_model=FacFacturaResponse)
def actualizar(
    id: uuid.UUID,
    body: FacFacturaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.actualizar(db, id, body, actor)


@router.post("/{id}/contabilizar", response_model=FacFacturaResponse)
def contabilizar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.contabilizar(db, id, actor)


@router.post("/{id}/anular", response_model=FacFacturaResponse)
def anular(
    id: uuid.UUID,
    body: AnularFacturaRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return facturacion_service.anular(db, id, body, actor)
