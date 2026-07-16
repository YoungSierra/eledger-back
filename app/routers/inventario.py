import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.inventario import (
    BodegaCreate, BodegaUpdate, BodegaResponse,
    FamiliaCreate, FamiliaUpdate, FamiliaResponse,
    UnidadMedidaCreate, UnidadMedidaUpdate, UnidadMedidaResponse,
    TipoProductoUpdate, TipoProductoResponse,
    ProductoCreate, ProductoUpdate, ProductoResponse,
    ProductoUmCreate, ProductoUmUpdate, ProductoUmResponse,
    SaldoListResponse, KardexResponse,
    MovimientoListResponse, MovimientoDetalle, MovimientoManualCreate,
)
from app.services import inventario_service

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/bodegas", response_model=list[BodegaResponse])
def listar_bodegas(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_bodegas(db, solo_activas)


@router.post("/bodegas", response_model=BodegaResponse, status_code=201)
def crear_bodega(
    body: BodegaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.crear_bodega(db, body, actor)


@router.put("/bodegas/{id}", response_model=BodegaResponse)
def actualizar_bodega(
    id: uuid.UUID,
    body: BodegaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.actualizar_bodega(db, id, body, actor)


# ---------------------------------------------------------------------------
# Familias
# ---------------------------------------------------------------------------

@router.get("/familias", response_model=list[FamiliaResponse])
def listar_familias(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_familias(db, solo_activas)


@router.post("/familias", response_model=FamiliaResponse, status_code=201)
def crear_familia(
    body: FamiliaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.crear_familia(db, body, actor)


@router.put("/familias/{id}", response_model=FamiliaResponse)
def actualizar_familia(
    id: uuid.UUID,
    body: FamiliaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.actualizar_familia(db, id, body, actor)


# ---------------------------------------------------------------------------
# Unidades de medida
# ---------------------------------------------------------------------------

@router.get("/unidades-medida", response_model=list[UnidadMedidaResponse])
def listar_unidades(
    solo_activas: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_unidades(db, solo_activas)


@router.post("/unidades-medida", response_model=UnidadMedidaResponse, status_code=201)
def crear_unidad(
    body: UnidadMedidaCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.crear_unidad(db, body)


@router.put("/unidades-medida/{id}", response_model=UnidadMedidaResponse)
def actualizar_unidad(
    id: uuid.UUID,
    body: UnidadMedidaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.actualizar_unidad(db, id, body)


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

@router.get("/productos", response_model=list[ProductoResponse])
def listar_productos(
    solo_activos: bool = Query(False),
    solo_inventariables: bool = Query(False),
    q: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_productos(db, solo_activos, q, limit, solo_inventariables)


@router.post("/productos", response_model=ProductoResponse, status_code=201)
def crear_producto(
    body: ProductoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.crear_producto(db, body, actor)


@router.put("/productos/{id}", response_model=ProductoResponse)
def actualizar_producto(
    id: uuid.UUID,
    body: ProductoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.actualizar_producto(db, id, body, actor)


# ---------------------------------------------------------------------------
# Tipos de producto
# ---------------------------------------------------------------------------

@router.get("/tipos-producto", response_model=list[TipoProductoResponse])
def listar_tipos(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_tipos_producto(db)


@router.put("/tipos-producto/{id}", response_model=TipoProductoResponse)
def actualizar_tipo(
    id: uuid.UUID,
    body: TipoProductoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.actualizar_tipo_producto(db, id, body, actor)


# ---------------------------------------------------------------------------
# Producto — Unidades de medida alternas
# ---------------------------------------------------------------------------

@router.get("/productos/{producto_id}/unidades", response_model=list[ProductoUmResponse])
def listar_producto_um(
    producto_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_producto_um(db, producto_id)


@router.post("/productos/{producto_id}/unidades", response_model=ProductoUmResponse, status_code=201)
def agregar_producto_um(
    producto_id: uuid.UUID,
    body: ProductoUmCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.agregar_producto_um(db, producto_id, body)


@router.put("/productos/{producto_id}/unidades/{um_id}", response_model=ProductoUmResponse)
def actualizar_producto_um(
    producto_id: uuid.UUID,
    um_id: uuid.UUID,
    body: ProductoUmUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.actualizar_producto_um(db, producto_id, um_id, body)


@router.delete("/productos/{producto_id}/unidades/{um_id}", status_code=204)
def eliminar_producto_um(
    producto_id: uuid.UUID,
    um_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    inventario_service.eliminar_producto_um(db, producto_id, um_id)


# ---------------------------------------------------------------------------
# Saldos de inventario
# ---------------------------------------------------------------------------

@router.get("/saldos", response_model=SaldoListResponse)
def listar_saldos(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(30, ge=1, le=100),
    bodega_id: Optional[uuid.UUID] = Query(None),
    producto_id: Optional[uuid.UUID] = Query(None),
    q: Optional[str] = Query(None),
    solo_con_stock: bool = Query(True),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_saldos(db, pagina, por_pagina, bodega_id, producto_id, q, solo_con_stock)


# ---------------------------------------------------------------------------
# Kardex
# ---------------------------------------------------------------------------

@router.get("/kardex", response_model=KardexResponse)
def obtener_kardex(
    producto_id: uuid.UUID = Query(...),
    bodega_id: Optional[uuid.UUID] = Query(None),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.obtener_kardex(db, producto_id, bodega_id, desde, hasta)


@router.get("/movimientos", response_model=MovimientoListResponse)
def listar_movimientos(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    tipo: Optional[str] = Query(None),
    bodega_id: Optional[uuid.UUID] = Query(None),
    estado: Optional[str] = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_movimientos(db, fecha_desde, fecha_hasta, tipo, bodega_id, estado, pagina, por_pagina)


@router.get("/movimientos/{movimiento_id}", response_model=MovimientoDetalle)
def obtener_movimiento(
    movimiento_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.obtener_movimiento(db, movimiento_id)


@router.post("/movimientos", response_model=MovimientoDetalle, status_code=201)
def crear_movimiento(
    data: MovimientoManualCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.crear_movimiento(db, data, actor)


@router.put("/movimientos/{movimiento_id}", response_model=MovimientoDetalle)
def editar_movimiento(
    movimiento_id: uuid.UUID,
    data: MovimientoManualCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.editar_movimiento(db, movimiento_id, data, actor)


@router.post("/movimientos/{movimiento_id}/publicar", response_model=MovimientoDetalle)
def publicar_movimiento(
    movimiento_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.publicar_movimiento(db, movimiento_id, actor)
