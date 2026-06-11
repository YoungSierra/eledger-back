import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.admin import AdmUsuario
from app.models.contabilidad import CntCuenta
from app.models.inventario import InvBodega, InvFamilia, InvUnidadMedida, InvTipoProducto, InvProducto, InvProductoUm
from app.schemas.auth import UsuarioActual
from app.schemas.inventario import (
    BodegaCreate, BodegaUpdate, BodegaResponse,
    FamiliaCreate, FamiliaUpdate, FamiliaResponse,
    UnidadMedidaCreate, UnidadMedidaUpdate, UnidadMedidaResponse,
    TipoProductoUpdate, TipoProductoResponse,
    ProductoCreate, ProductoUpdate, ProductoResponse,
    ProductoUmCreate, ProductoUmUpdate, ProductoUmResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cuenta_display(db: Session, id: Optional[uuid.UUID]) -> Optional[str]:
    if not id:
        return None
    c = db.query(CntCuenta).filter(CntCuenta.id == id).first()
    return f"{c.codigo} — {c.nombre}" if c else None


def _familia_to_response(db: Session, obj: InvFamilia) -> FamiliaResponse:
    return FamiliaResponse(
        id=obj.id,
        codigo=obj.codigo,
        nombre=obj.nombre,
        descripcion=obj.descripcion,
        cuenta_inventario_id=obj.cuenta_inventario_id,
        cuenta_inventario_display=_cuenta_display(db, obj.cuenta_inventario_id),
        cuenta_costo_ventas_id=obj.cuenta_costo_ventas_id,
        cuenta_costo_ventas_display=_cuenta_display(db, obj.cuenta_costo_ventas_id),
        cuenta_ingreso_id=obj.cuenta_ingreso_id,
        cuenta_ingreso_display=_cuenta_display(db, obj.cuenta_ingreso_id),
        cuenta_devolucion_venta_id=obj.cuenta_devolucion_venta_id,
        cuenta_devolucion_venta_display=_cuenta_display(db, obj.cuenta_devolucion_venta_id),
        cuenta_devolucion_compra_id=obj.cuenta_devolucion_compra_id,
        cuenta_devolucion_compra_display=_cuenta_display(db, obj.cuenta_devolucion_compra_id),
        cuenta_ajuste_entrada_id=obj.cuenta_ajuste_entrada_id,
        cuenta_ajuste_entrada_display=_cuenta_display(db, obj.cuenta_ajuste_entrada_id),
        cuenta_ajuste_salida_id=obj.cuenta_ajuste_salida_id,
        cuenta_ajuste_salida_display=_cuenta_display(db, obj.cuenta_ajuste_salida_id),
        activo=obj.activo,
    )


# ---------------------------------------------------------------------------
# Familias
# ---------------------------------------------------------------------------

def listar_familias(db: Session, solo_activas: bool = False) -> list[FamiliaResponse]:
    q = db.query(InvFamilia)
    if solo_activas:
        q = q.filter(InvFamilia.activo == True)
    return [_familia_to_response(db, f) for f in q.order_by(InvFamilia.codigo).all()]


def crear_familia(db: Session, data: FamiliaCreate, actor: UsuarioActual) -> FamiliaResponse:
    codigo = data.codigo.strip().upper()
    if db.query(InvFamilia).filter(InvFamilia.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe una familia con ese código")
    obj = InvFamilia(
        codigo=codigo,
        nombre=data.nombre.strip(),
        descripcion=data.descripcion.strip() if data.descripcion else None,
        cuenta_inventario_id=data.cuenta_inventario_id,
        cuenta_costo_ventas_id=data.cuenta_costo_ventas_id,
        cuenta_ingreso_id=data.cuenta_ingreso_id,
        cuenta_devolucion_venta_id=data.cuenta_devolucion_venta_id,
        cuenta_devolucion_compra_id=data.cuenta_devolucion_compra_id,
        cuenta_ajuste_entrada_id=data.cuenta_ajuste_entrada_id,
        cuenta_ajuste_salida_id=data.cuenta_ajuste_salida_id,
        activo=True,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _familia_to_response(db, obj)


def actualizar_familia(db: Session, id: uuid.UUID, data: FamiliaUpdate, actor: UsuarioActual) -> FamiliaResponse:
    obj = db.query(InvFamilia).filter(InvFamilia.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Familia no encontrada")
    if data.nombre is not None:
        obj.nombre = data.nombre.strip()
    if data.descripcion is not None:
        obj.descripcion = data.descripcion.strip() or None
    for campo in [
        "cuenta_inventario_id", "cuenta_costo_ventas_id", "cuenta_ingreso_id",
        "cuenta_devolucion_venta_id", "cuenta_devolucion_compra_id",
        "cuenta_ajuste_entrada_id", "cuenta_ajuste_salida_id",
    ]:
        val = getattr(data, campo)
        if val is not None:
            setattr(obj, campo, val)
    if data.activo is not None:
        obj.activo = data.activo
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return _familia_to_response(db, obj)


# ---------------------------------------------------------------------------
# Tipos de producto
# ---------------------------------------------------------------------------

CUENTAS_TIPO = [
    "cuenta_inventario_id", "cuenta_costo_ventas_id", "cuenta_ingreso_id",
    "cuenta_devolucion_venta_id", "cuenta_devolucion_compra_id",
    "cuenta_ajuste_entrada_id", "cuenta_ajuste_salida_id",
]

ORDEN_TIPOS = ['MERCANCIA', 'SERVICIO', 'MATERIA_PRIMA', 'INSUMO']


def _tipo_to_response(db: Session, obj: InvTipoProducto) -> TipoProductoResponse:
    return TipoProductoResponse(
        id=obj.id,
        codigo=obj.codigo,
        nombre=obj.nombre,
        maneja_inventario=obj.maneja_inventario,
        cuenta_inventario_id=obj.cuenta_inventario_id,
        cuenta_inventario_display=_cuenta_display(db, obj.cuenta_inventario_id),
        cuenta_costo_ventas_id=obj.cuenta_costo_ventas_id,
        cuenta_costo_ventas_display=_cuenta_display(db, obj.cuenta_costo_ventas_id),
        cuenta_ingreso_id=obj.cuenta_ingreso_id,
        cuenta_ingreso_display=_cuenta_display(db, obj.cuenta_ingreso_id),
        cuenta_devolucion_venta_id=obj.cuenta_devolucion_venta_id,
        cuenta_devolucion_venta_display=_cuenta_display(db, obj.cuenta_devolucion_venta_id),
        cuenta_devolucion_compra_id=obj.cuenta_devolucion_compra_id,
        cuenta_devolucion_compra_display=_cuenta_display(db, obj.cuenta_devolucion_compra_id),
        cuenta_ajuste_entrada_id=obj.cuenta_ajuste_entrada_id,
        cuenta_ajuste_entrada_display=_cuenta_display(db, obj.cuenta_ajuste_entrada_id),
        cuenta_ajuste_salida_id=obj.cuenta_ajuste_salida_id,
        cuenta_ajuste_salida_display=_cuenta_display(db, obj.cuenta_ajuste_salida_id),
    )


def listar_tipos_producto(db: Session) -> list[TipoProductoResponse]:
    rows = db.query(InvTipoProducto).all()
    rows.sort(key=lambda r: ORDEN_TIPOS.index(r.codigo) if r.codigo in ORDEN_TIPOS else 99)
    return [_tipo_to_response(db, r) for r in rows]


def actualizar_tipo_producto(
    db: Session, id: uuid.UUID, data: TipoProductoUpdate, actor: UsuarioActual
) -> TipoProductoResponse:
    obj = db.query(InvTipoProducto).filter(InvTipoProducto.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tipo de producto no encontrado")
    for campo in CUENTAS_TIPO:
        val = getattr(data, campo)
        if val is not None:
            setattr(obj, campo, val)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return _tipo_to_response(db, obj)


# ---------------------------------------------------------------------------
# Unidades de medida
# ---------------------------------------------------------------------------

def listar_unidades(db: Session, solo_activas: bool = False) -> list[UnidadMedidaResponse]:
    q = db.query(InvUnidadMedida)
    if solo_activas:
        q = q.filter(InvUnidadMedida.activo == True)
    return q.order_by(InvUnidadMedida.codigo).all()


def crear_unidad(db: Session, data: UnidadMedidaCreate) -> UnidadMedidaResponse:
    codigo = data.codigo.strip().upper()
    if db.query(InvUnidadMedida).filter(InvUnidadMedida.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe una unidad con ese código")
    obj = InvUnidadMedida(codigo=codigo, nombre=data.nombre.strip(), activo=True)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def actualizar_unidad(db: Session, id: uuid.UUID, data: UnidadMedidaUpdate) -> UnidadMedidaResponse:
    obj = db.query(InvUnidadMedida).filter(InvUnidadMedida.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
    if data.nombre is not None:
        obj.nombre = data.nombre.strip()
    if data.activo is not None:
        obj.activo = data.activo
    db.commit()
    db.refresh(obj)
    return obj


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

CUENTAS_PRODUCTO = [
    "cuenta_inventario_id", "cuenta_costo_ventas_id", "cuenta_ingreso_id",
    "cuenta_devolucion_venta_id", "cuenta_devolucion_compra_id",
    "cuenta_ajuste_entrada_id", "cuenta_ajuste_salida_id",
]


def _producto_to_response(db: Session, obj: InvProducto) -> ProductoResponse:
    return ProductoResponse(
        id=obj.id,
        codigo=obj.codigo,
        nombre=obj.nombre,
        descripcion=obj.descripcion,
        tipo_id=obj.tipo_id,
        tipo_codigo=obj.tipo.codigo,
        tipo_nombre=obj.tipo.nombre,
        familia_id=obj.familia_id,
        familia_nombre=obj.familia.nombre if obj.familia else None,
        um_base_id=obj.um_base_id,
        um_base_codigo=obj.um_base.codigo,
        um_base_nombre=obj.um_base.nombre,
        maneja_inventario=obj.maneja_inventario,
        maneja_series=obj.maneja_series,
        maneja_lotes=obj.maneja_lotes,
        cuenta_inventario_id=obj.cuenta_inventario_id,
        cuenta_inventario_display=_cuenta_display(db, obj.cuenta_inventario_id),
        cuenta_costo_ventas_id=obj.cuenta_costo_ventas_id,
        cuenta_costo_ventas_display=_cuenta_display(db, obj.cuenta_costo_ventas_id),
        cuenta_ingreso_id=obj.cuenta_ingreso_id,
        cuenta_ingreso_display=_cuenta_display(db, obj.cuenta_ingreso_id),
        cuenta_devolucion_venta_id=obj.cuenta_devolucion_venta_id,
        cuenta_devolucion_venta_display=_cuenta_display(db, obj.cuenta_devolucion_venta_id),
        cuenta_devolucion_compra_id=obj.cuenta_devolucion_compra_id,
        cuenta_devolucion_compra_display=_cuenta_display(db, obj.cuenta_devolucion_compra_id),
        cuenta_ajuste_entrada_id=obj.cuenta_ajuste_entrada_id,
        cuenta_ajuste_entrada_display=_cuenta_display(db, obj.cuenta_ajuste_entrada_id),
        cuenta_ajuste_salida_id=obj.cuenta_ajuste_salida_id,
        cuenta_ajuste_salida_display=_cuenta_display(db, obj.cuenta_ajuste_salida_id),
        activo=obj.activo,
    )


def listar_productos(db: Session, solo_activos: bool = False) -> list[ProductoResponse]:
    q = db.query(InvProducto)
    if solo_activos:
        q = q.filter(InvProducto.activo == True)
    return [_producto_to_response(db, p) for p in q.order_by(InvProducto.codigo).all()]


def crear_producto(db: Session, data: ProductoCreate, actor: UsuarioActual) -> ProductoResponse:
    codigo = data.codigo.strip().upper()
    if db.query(InvProducto).filter(InvProducto.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe un producto con ese código")
    if not db.query(InvUnidadMedida).filter(InvUnidadMedida.id == data.um_base_id).first():
        raise HTTPException(status_code=400, detail="Unidad de medida no encontrada")
    if not db.query(InvTipoProducto).filter(InvTipoProducto.id == data.tipo_id).first():
        raise HTTPException(status_code=400, detail="Tipo de producto no encontrado")
    obj = InvProducto(
        codigo=codigo,
        nombre=data.nombre.strip(),
        descripcion=data.descripcion.strip() if data.descripcion else None,
        tipo_id=data.tipo_id,
        familia_id=data.familia_id,
        um_base_id=data.um_base_id,
        maneja_inventario=data.maneja_inventario,
        maneja_series=data.maneja_series,
        maneja_lotes=data.maneja_lotes,
        tiene_variantes=False,
        **{c: getattr(data, c) for c in CUENTAS_PRODUCTO},
        activo=True,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _producto_to_response(db, obj)


def actualizar_producto(db: Session, id: uuid.UUID, data: ProductoUpdate, actor: UsuarioActual) -> ProductoResponse:
    obj = db.query(InvProducto).filter(InvProducto.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    simple = ["nombre", "descripcion", "tipo_id", "familia_id", "um_base_id",
              "maneja_inventario", "maneja_series", "maneja_lotes", "activo"] + CUENTAS_PRODUCTO
    for campo in simple:
        val = getattr(data, campo)
        if val is not None:
            setattr(obj, campo, val.strip() if isinstance(val, str) else val)
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return _producto_to_response(db, obj)


# ---------------------------------------------------------------------------
# Producto — Unidades de medida alternas
# ---------------------------------------------------------------------------

def _um_to_response(obj: InvProductoUm) -> ProductoUmResponse:
    return ProductoUmResponse(
        id=obj.id,
        producto_id=obj.producto_id,
        um_id=obj.um_id,
        um_codigo=obj.um.codigo,
        um_nombre=obj.um.nombre,
        factor=obj.factor,
        es_compra=obj.es_compra,
        es_venta=obj.es_venta,
        activo=obj.activo,
    )


def listar_producto_um(db: Session, producto_id: uuid.UUID) -> list[ProductoUmResponse]:
    if not db.query(InvProducto).filter(InvProducto.id == producto_id).first():
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    rows = (
        db.query(InvProductoUm)
        .filter(InvProductoUm.producto_id == producto_id, InvProductoUm.activo == True)
        .all()
    )
    return [_um_to_response(r) for r in rows]


def agregar_producto_um(
    db: Session, producto_id: uuid.UUID, data: ProductoUmCreate
) -> ProductoUmResponse:
    producto = db.query(InvProducto).filter(InvProducto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    um = db.query(InvUnidadMedida).filter(InvUnidadMedida.id == data.um_id).first()
    if not um:
        raise HTTPException(status_code=400, detail="Unidad de medida no encontrada")
    if um.id == producto.um_base_id:
        raise HTTPException(status_code=400, detail="No se puede agregar la unidad base como alterna")
    existe = db.query(InvProductoUm).filter(
        InvProductoUm.producto_id == producto_id,
        InvProductoUm.um_id == data.um_id,
    ).first()
    if existe:
        if not existe.activo:
            existe.activo = True
            existe.factor = data.factor
            existe.es_compra = data.es_compra
            existe.es_venta = data.es_venta
            db.commit()
            db.refresh(existe)
            return _um_to_response(existe)
        raise HTTPException(status_code=400, detail="Esa unidad ya está registrada para este producto")
    obj = InvProductoUm(
        producto_id=producto_id,
        um_id=data.um_id,
        factor=data.factor,
        es_compra=data.es_compra,
        es_venta=data.es_venta,
        activo=True,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _um_to_response(obj)


def actualizar_producto_um(
    db: Session, producto_id: uuid.UUID, um_id: uuid.UUID, data: ProductoUmUpdate
) -> ProductoUmResponse:
    obj = db.query(InvProductoUm).filter(
        InvProductoUm.id == um_id,
        InvProductoUm.producto_id == producto_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Unidad alterna no encontrada")
    if data.factor is not None:
        obj.factor = data.factor
    if data.es_compra is not None:
        obj.es_compra = data.es_compra
    if data.es_venta is not None:
        obj.es_venta = data.es_venta
    db.commit()
    db.refresh(obj)
    return _um_to_response(obj)


def eliminar_producto_um(db: Session, producto_id: uuid.UUID, um_id: uuid.UUID) -> None:
    obj = db.query(InvProductoUm).filter(
        InvProductoUm.id == um_id,
        InvProductoUm.producto_id == producto_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Unidad alterna no encontrada")
    obj.activo = False
    db.commit()


def _to_response(obj: InvBodega) -> BodegaResponse:
    nombre_responsable = None
    if obj.responsable:
        nombre_responsable = f"{obj.responsable.nombre} {obj.responsable.apellido}"
    return BodegaResponse(
        id=obj.id,
        codigo=obj.codigo,
        nombre=obj.nombre,
        direccion=obj.direccion,
        responsable_id=obj.responsable_id,
        responsable_nombre=nombre_responsable,
        activo=obj.activo,
    )


def listar_bodegas(db: Session, solo_activas: bool = False) -> list[BodegaResponse]:
    q = db.query(InvBodega)
    if solo_activas:
        q = q.filter(InvBodega.activo == True)
    return [_to_response(b) for b in q.order_by(InvBodega.codigo).all()]


def crear_bodega(db: Session, data: BodegaCreate, actor: UsuarioActual) -> BodegaResponse:
    codigo = data.codigo.strip().upper()
    if db.query(InvBodega).filter(InvBodega.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe una bodega con ese código")
    if data.responsable_id and not db.query(AdmUsuario).filter(AdmUsuario.id == data.responsable_id).first():
        raise HTTPException(status_code=400, detail="Responsable no encontrado")
    obj = InvBodega(
        codigo=codigo,
        nombre=data.nombre.strip(),
        direccion=data.direccion.strip() if data.direccion else None,
        responsable_id=data.responsable_id,
        activo=True,
        creado_por=uuid.UUID(actor.id),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_response(obj)


def actualizar_bodega(db: Session, id: uuid.UUID, data: BodegaUpdate, actor: UsuarioActual) -> BodegaResponse:
    obj = db.query(InvBodega).filter(InvBodega.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    if data.nombre is not None:
        obj.nombre = data.nombre.strip()
    if data.direccion is not None:
        obj.direccion = data.direccion.strip() or None
    if data.responsable_id is not None:
        if not db.query(AdmUsuario).filter(AdmUsuario.id == data.responsable_id).first():
            raise HTTPException(status_code=400, detail="Responsable no encontrado")
        obj.responsable_id = data.responsable_id
    if data.activo is not None:
        obj.activo = data.activo
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return _to_response(obj)
