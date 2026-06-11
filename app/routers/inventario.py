import uuid

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
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return inventario_service.listar_productos(db, solo_activos)


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
