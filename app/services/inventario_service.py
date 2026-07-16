import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.admin import AdmMoneda, AdmTipoDocumento, AdmConsecutivo
from app.models.adm import AdmTercero
from app.models.contabilidad import CntAsiento, CntAsientoLinea, CntCuenta, CntPeriodo
from app.models.inventario import (
    InvBodega, InvFamilia, InvUnidadMedida, InvTipoProducto,
    InvProducto, InvProductoUm, InvProductoBodega, InvMovimiento, InvMovimientoLinea,
)
from app.schemas.auth import UsuarioActual
from app.schemas.inventario import (
    BodegaCreate, BodegaUpdate, BodegaResponse,
    FamiliaCreate, FamiliaUpdate, FamiliaResponse,
    UnidadMedidaCreate, UnidadMedidaUpdate, UnidadMedidaResponse,
    TipoProductoUpdate, TipoProductoResponse,
    ProductoCreate, ProductoUpdate, ProductoResponse,
    ProductoUmCreate, ProductoUmUpdate, ProductoUmResponse,
    SaldoProducto, SaldoListResponse, KardexLinea, KardexResponse,
    MovimientoListItem, MovimientoListResponse, MovimientoLineaDetalle,
    MovimientoDetalle, AjusteCreate,
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


def listar_productos(
    db: Session,
    solo_activos: bool = False,
    q_busqueda: Optional[str] = None,
    limit: int = 200,
    solo_inventariables: bool = False,
) -> list[ProductoResponse]:
    q = db.query(InvProducto)
    if solo_activos:
        q = q.filter(InvProducto.activo == True)
    if solo_inventariables:
        q = q.filter(InvProducto.maneja_inventario == True)
    if q_busqueda:
        term = f"%{q_busqueda}%"
        q = q.filter(
            (InvProducto.codigo.ilike(term)) | (InvProducto.nombre.ilike(term))
        )
    return [_producto_to_response(db, p) for p in q.order_by(InvProducto.codigo).limit(limit).all()]


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


# ---------------------------------------------------------------------------
# Saldos de inventario
# ---------------------------------------------------------------------------

def listar_saldos(
    db: Session,
    pagina: int = 1,
    por_pagina: int = 30,
    bodega_id: uuid.UUID | None = None,
    producto_id: uuid.UUID | None = None,
    q: str | None = None,
    solo_con_stock: bool = True,
) -> SaldoListResponse:
    query = (
        db.query(InvProductoBodega)
        .join(InvProductoBodega.producto)
        .join(InvProductoBodega.bodega)
    )
    if bodega_id:
        query = query.filter(InvProductoBodega.bodega_id == bodega_id)
    if producto_id:
        query = query.filter(InvProductoBodega.producto_id == producto_id)
    if solo_con_stock:
        query = query.filter(InvProductoBodega.cantidad > 0)
    if q:
        term = f"%{q}%"
        query = query.filter(
            InvProducto.codigo.ilike(term) | InvProducto.nombre.ilike(term)
        )

    total = query.count()
    rows = (
        query.order_by(InvProducto.codigo)
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    items = []
    for pb in rows:
        p = pb.producto
        b = pb.bodega
        items.append(SaldoProducto(
            producto_id=p.id,
            producto_codigo=p.codigo,
            producto_nombre=p.nombre,
            um_base_codigo=p.um_base.codigo if p.um_base else "",
            bodega_id=b.id,
            bodega_nombre=b.nombre,
            cantidad=pb.cantidad,
            costo_promedio=pb.costo_promedio,
            valor_total=pb.cantidad * pb.costo_promedio,
        ))
    return SaldoListResponse(items=items, total=total, pagina=pagina, por_pagina=por_pagina)


# ---------------------------------------------------------------------------
# Kardex
# ---------------------------------------------------------------------------

_TIPO_LABEL: dict[str, str] = {
    "ENTRADA_COMPRA": "Entrada compra",
    "SALIDA_VENTA": "Salida venta",
    "AJUSTE_ENTRADA": "Ajuste entrada",
    "AJUSTE_SALIDA": "Ajuste salida",
    "TRASLADO_SALIDA": "Traslado salida",
    "TRASLADO_ENTRADA": "Traslado entrada",
}
_TIPOS_SALIDA = {"SALIDA_VENTA", "AJUSTE_SALIDA", "TRASLADO_SALIDA"}


def obtener_kardex(
    db: Session,
    producto_id: uuid.UUID,
    bodega_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> KardexResponse:
    producto = db.get(InvProducto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    bodega = db.get(InvBodega, bodega_id) if bodega_id else None

    query = (
        db.query(InvMovimientoLinea)
        .join(InvMovimiento, InvMovimiento.id == InvMovimientoLinea.movimiento_id)
        .filter(
            InvMovimientoLinea.producto_id == producto_id,
            InvMovimiento.estado == "confirmado",
        )
    )
    if bodega_id:
        query = query.filter(InvMovimiento.bodega_id == bodega_id)
    if desde:
        query = query.filter(func.date(InvMovimiento.fecha) >= desde)
    if hasta:
        query = query.filter(func.date(InvMovimiento.fecha) <= hasta)

    lineas_raw = query.order_by(InvMovimiento.fecha, InvMovimiento.creado_en, InvMovimientoLinea.id).all()

    saldo_cant = Decimal("0")
    saldo_valor = Decimal("0")
    lineas: list[KardexLinea] = []

    for ml in lineas_raw:
        mov = ml.movimiento
        es_salida = mov.tipo in _TIPOS_SALIDA
        cantidad = ml.cantidad_base

        if es_salida:
            costo_unit = saldo_valor / saldo_cant if saldo_cant > 0 else ml.costo_unitario
            ct = (cantidad * costo_unit).quantize(Decimal("0.0001"))
            saldo_cant -= cantidad
            saldo_valor -= ct
            entrada, salida = Decimal("0"), cantidad
        else:
            costo_unit = ml.costo_unitario
            ct = ml.costo_total
            saldo_cant += cantidad
            saldo_valor += ct
            entrada, salida = cantidad, Decimal("0")

        saldo_cant = max(saldo_cant, Decimal("0"))
        saldo_valor = max(saldo_valor, Decimal("0"))

        lineas.append(KardexLinea(
            fecha=mov.fecha.strftime("%Y-%m-%d"),
            movimiento_id=mov.id,
            numero=mov.numero,
            tipo=_TIPO_LABEL.get(mov.tipo, mov.tipo),
            descripcion=mov.descripcion,
            origen_tipo=mov.origen_tipo,
            origen_id=mov.origen_id,
            cantidad_entrada=entrada,
            cantidad_salida=salida,
            costo_unitario=costo_unit,
            costo_total=ct,
            saldo_cantidad=saldo_cant,
            saldo_valor=saldo_valor,
            costo_promedio=saldo_valor / saldo_cant if saldo_cant > 0 else Decimal("0"),
        ))

    return KardexResponse(
        producto_id=producto.id,
        producto_codigo=producto.codigo,
        producto_nombre=producto.nombre,
        bodega_id=bodega_id,
        bodega_nombre=bodega.nombre if bodega else None,
        lineas=lineas,
    )

# ---------------------------------------------------------------------------
# Helpers movimientos
# ---------------------------------------------------------------------------

_TIPO_LABEL_MOV = {
    "ENTRADA_COMPRA":      "Entrada compra",
    "SALIDA_VENTA":        "Salida venta",
    "TRASLADO_SALIDA":     "Traslado salida",
    "TRASLADO_ENTRADA":    "Traslado entrada",
    "AJUSTE_ENTRADA":      "Ajuste entrada",
    "AJUSTE_SALIDA":       "Ajuste salida",
    "DEVOLUCION_CLIENTE":  "Devolucion cliente",
    "DEVOLUCION_PROVEEDOR":"Devolucion proveedor",
    "ENTRADA_PRODUCCION":  "Entrada produccion",
    "SALIDA_PRODUCCION":   "Salida produccion",
}


def _buscar_periodo_inv(db, fecha):
    from app.models.contabilidad import CntPeriodo
    p = db.query(CntPeriodo).filter(
        CntPeriodo.fecha_inicio <= fecha,
        CntPeriodo.fecha_cierre >= fecha,
        CntPeriodo.estado == "abierto",
        CntPeriodo.activo == True,
    ).first()
    if not p:
        raise HTTPException(status_code=400, detail=f"No existe periodo contable abierto para {fecha}")
    return p


def _resolver_cuenta_inventario_inv(db, producto):
    if producto.cuenta_inventario_id:
        return db.get(CntCuenta, producto.cuenta_inventario_id)
    if producto.familia_id:
        fam = db.get(InvFamilia, producto.familia_id)
        if fam and fam.cuenta_inventario_id:
            return db.get(CntCuenta, fam.cuenta_inventario_id)
    tipo = db.get(InvTipoProducto, producto.tipo_id)
    if tipo and tipo.cuenta_inventario_id:
        return db.get(CntCuenta, tipo.cuenta_inventario_id)
    return None


def _resolver_cuenta_ajuste(db, producto, campo):
    val = getattr(producto, campo, None)
    if val:
        return db.get(CntCuenta, val)
    if producto.familia_id:
        fam = db.get(InvFamilia, producto.familia_id)
        if fam:
            val = getattr(fam, campo, None)
            if val:
                return db.get(CntCuenta, val)
    tipo = db.get(InvTipoProducto, producto.tipo_id)
    if tipo:
        val = getattr(tipo, campo, None)
        if val:
            return db.get(CntCuenta, val)
    return None


def _generar_numero(db, codigo_tipo: str):
    """Genera el siguiente consecutivo para un tipo de documento. Retorna (td_id, numero_str)."""
    td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == codigo_tipo).first()
    if not td:
        return None, None
    cons = db.query(AdmConsecutivo).filter(AdmConsecutivo.tipo_documento_id == td.id).with_for_update().first()
    if not cons:
        return td.id, f"{codigo_tipo}-0001"
    siguiente = cons.numero_actual + 1
    cons.numero_actual = siguiente
    return td.id, f"{cons.prefijo or ''}{str(siguiente).zfill(cons.longitud_minima)}"


def _generar_numero_ajuste(db):
    return _generar_numero(db, "AJ")


# ---------------------------------------------------------------------------
# Listar movimientos
# ---------------------------------------------------------------------------

def listar_movimientos(
    db,
    fecha_desde=None,
    fecha_hasta=None,
    tipo=None,
    bodega_id=None,
    estado=None,
    pagina=1,
    por_pagina=30,
):
    from app.models.inventario import InvMovimiento, InvMovimientoLinea, InvBodega
    from sqlalchemy import func

    q = db.query(
        InvMovimiento,
        InvBodega.nombre.label("bodega_nombre"),
    ).join(InvBodega, InvBodega.id == InvMovimiento.bodega_id)

    # Los traslados se muestran como una sola fila (TRASLADO_SALIDA lleva ambas bodegas)
    q = q.filter(InvMovimiento.tipo != "TRASLADO_ENTRADA")

    if fecha_desde:
        q = q.filter(InvMovimiento.fecha >= fecha_desde)
    if fecha_hasta:
        from datetime import timedelta
        q = q.filter(InvMovimiento.fecha < fecha_hasta + timedelta(days=1))
    if tipo:
        q = q.filter(InvMovimiento.tipo == tipo)
    if bodega_id:
        q = q.filter(
            (InvMovimiento.bodega_id == bodega_id) | (InvMovimiento.bodega_destino_id == bodega_id)
        )
    if estado:
        q = q.filter(InvMovimiento.estado == estado)

    total = q.count()
    rows = q.order_by(InvMovimiento.fecha.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    items = []
    for mov, bodega_nombre in rows:
        lineas = mov.lineas
        costo_total = sum(ln.costo_total for ln in lineas)
        bodega_dest = db.get(InvBodega, mov.bodega_destino_id) if mov.bodega_destino_id else None
        items.append(MovimientoListItem(
            id=mov.id,
            numero=mov.numero,
            tipo=mov.tipo,
            fecha=str(mov.fecha.date()) if hasattr(mov.fecha, "date") else str(mov.fecha),
            bodega_id=mov.bodega_id,
            bodega_nombre=bodega_nombre,
            bodega_destino_nombre=bodega_dest.nombre if bodega_dest else None,
            descripcion=mov.descripcion,
            estado=mov.estado,
            origen_tipo=mov.origen_tipo,
            origen_id=mov.origen_id,
            num_lineas=len(lineas),
            costo_total=costo_total,
        ))

    return MovimientoListResponse(items=items, total=total, pagina=pagina, por_pagina=por_pagina)


# ---------------------------------------------------------------------------
# Detalle de movimiento
# ---------------------------------------------------------------------------

def obtener_movimiento(db, movimiento_id):
    from app.models.inventario import InvMovimiento, InvBodega

    mov = db.get(InvMovimiento, movimiento_id)
    if not mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")

    bodega = db.get(InvBodega, mov.bodega_id)
    bodega_dest = db.get(InvBodega, mov.bodega_destino_id) if mov.bodega_destino_id else None

    lineas = []
    costo_total = Decimal("0")
    for ln in mov.lineas:
        p = ln.producto
        um = ln.um
        lineas.append(MovimientoLineaDetalle(
            id=ln.id,
            producto_id=ln.producto_id,
            producto_codigo=p.codigo if p else "",
            producto_nombre=p.nombre if p else "",
            cantidad=ln.cantidad,
            um_id=ln.um_id,
            um_codigo=um.codigo if um else "",
            costo_unitario=ln.costo_unitario,
            costo_total=ln.costo_total,
        ))
        costo_total += ln.costo_total

    return MovimientoDetalle(
        id=mov.id,
        numero=mov.numero,
        tipo=mov.tipo,
        fecha=str(mov.fecha.date()) if hasattr(mov.fecha, "date") else str(mov.fecha),
        bodega_id=mov.bodega_id,
        bodega_nombre=bodega.nombre if bodega else "",
        bodega_destino_id=mov.bodega_destino_id,
        bodega_destino_nombre=bodega_dest.nombre if bodega_dest else None,
        descripcion=mov.descripcion,
        estado=mov.estado,
        origen_tipo=mov.origen_tipo,
        origen_id=mov.origen_id,
        asiento_id=mov.asiento_id,
        lineas=lineas,
        costo_total=costo_total,
    )


# ---------------------------------------------------------------------------
# Crear ajuste de inventario
# ---------------------------------------------------------------------------

def _aplicar_linea_movimiento(db, mov_id, linea, bodega_id, actor_id):
    """Crea InvMovimientoLinea y retorna (cantidad_base, costo_unitario, costo_total, producto)."""
    producto = db.get(InvProducto, linea.producto_id)
    if not producto:
        raise HTTPException(status_code=400, detail=f"Producto {linea.producto_id} no encontrado")

    factor = Decimal("1")
    pu = db.query(InvProductoUm).filter(
        InvProductoUm.producto_id == linea.producto_id,
        InvProductoUm.um_id == linea.um_id,
    ).first()
    if pu:
        factor = pu.factor

    cantidad_base = linea.cantidad * factor
    costo_total_ln = cantidad_base * linea.costo_unitario

    db.add(InvMovimientoLinea(
        movimiento_id=mov_id,
        producto_id=linea.producto_id,
        cantidad=linea.cantidad,
        um_id=linea.um_id,
        cantidad_base=cantidad_base,
        costo_unitario=linea.costo_unitario,
        costo_total=costo_total_ln,
    ))
    return cantidad_base, linea.costo_unitario, costo_total_ln, producto


def _get_or_create_pb(db, producto_id, bodega_id):
    pb = db.query(InvProductoBodega).filter(
        InvProductoBodega.producto_id == producto_id,
        InvProductoBodega.bodega_id == bodega_id,
    ).with_for_update().first()
    if not pb:
        pb = InvProductoBodega(producto_id=producto_id, bodega_id=bodega_id,
                               cantidad=Decimal("0"), costo_promedio=Decimal("0"))
        db.add(pb); db.flush()
    return pb


def _validar_stock(db, producto_id, bodega_id, um_id, cantidad):
    """Lanza 400 si no hay suficiente stock. Retorna qty_base."""
    factor = Decimal("1")
    pu = db.query(InvProductoUm).filter(
        InvProductoUm.producto_id == producto_id,
        InvProductoUm.um_id == um_id,
    ).first()
    if pu:
        factor = pu.factor
    qty_b = cantidad * factor
    pb = db.query(InvProductoBodega).filter(
        InvProductoBodega.producto_id == producto_id,
        InvProductoBodega.bodega_id == bodega_id,
    ).first()
    disponible = pb.cantidad if pb else Decimal("0")
    if disponible < qty_b:
        prod = db.get(InvProducto, producto_id)
        nombre = prod.nombre if prod else str(producto_id)
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente para '{nombre}': disponible {disponible}, requerido {qty_b}",
        )
    return qty_b


def _publicar_movimiento_interno(db, mov, actor_id):
    """Aplica efectos de stock y contabilidad a un movimiento en borrador."""
    from datetime import datetime as _dt
    from app.schemas.inventario import MovimientoLineaCreate as MLC

    es_traslado = mov.tipo in ("TRASLADO_SALIDA", "TRASLADO_ENTRADA")
    fecha = mov.fecha.date() if hasattr(mov.fecha, "date") else mov.fecha

    # Buscar movimiento de entrada asociado para traslado (mismo numero)
    mov_ent = None
    if mov.tipo == "TRASLADO_SALIDA" and mov.numero:
        from app.models.inventario import InvMovimiento as _Mov
        mov_ent = db.query(_Mov).filter(
            _Mov.tipo == "TRASLADO_ENTRADA",
            _Mov.numero == mov.numero,
            _Mov.estado == "borrador",
        ).first()

    for ln in mov.lineas:
        factor = Decimal("1")
        pu = db.query(InvProductoUm).filter(
            InvProductoUm.producto_id == ln.producto_id,
            InvProductoUm.um_id == ln.um_id,
        ).first()
        if pu:
            factor = pu.factor
        qty_b = ln.cantidad_base

        if mov.tipo == "TRASLADO_SALIDA":
            # Validar y reducir origen
            pb_orig = _get_or_create_pb(db, ln.producto_id, mov.bodega_id)
            if pb_orig.cantidad < qty_b:
                prod = db.get(InvProducto, ln.producto_id)
                raise HTTPException(status_code=400,
                    detail=f"Stock insuficiente para '{prod.nombre if prod else ln.producto_id}'")
            pb_orig.cantidad -= qty_b
            # Aumentar destino
            pb_dest = _get_or_create_pb(db, ln.producto_id, mov.bodega_destino_id)
            stock_ant = pb_dest.cantidad; costo_ant = pb_dest.costo_promedio
            nueva_cant = stock_ant + qty_b
            pb_dest.cantidad = nueva_cant
            pb_dest.costo_promedio = (
                (stock_ant * costo_ant + ln.costo_total) / nueva_cant if nueva_cant > 0 else ln.costo_unitario
            )

        elif mov.tipo == "AJUSTE_ENTRADA":
            pb = _get_or_create_pb(db, ln.producto_id, mov.bodega_id)
            stock_ant = pb.cantidad; costo_ant = pb.costo_promedio
            nueva_cant = stock_ant + qty_b
            pb.cantidad = nueva_cant
            pb.costo_promedio = (
                (stock_ant * costo_ant + ln.costo_total) / nueva_cant if nueva_cant > 0 else ln.costo_unitario
            )

        elif mov.tipo == "AJUSTE_SALIDA":
            pb = _get_or_create_pb(db, ln.producto_id, mov.bodega_id)
            if pb.cantidad < qty_b:
                prod = db.get(InvProducto, ln.producto_id)
                raise HTTPException(status_code=400,
                    detail=f"Stock insuficiente para '{prod.nombre if prod else ln.producto_id}'")
            pb.cantidad -= qty_b

    mov.estado = "confirmado"
    if mov_ent:
        mov_ent.estado = "confirmado"

    # Asiento contable (solo ajustes)
    if mov.tipo in ("AJUSTE_ENTRADA", "AJUSTE_SALIDA"):
        moneda_func = db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.activo == True).first()
        costo_total_mov = sum(ln.costo_total for ln in mov.lineas)
        if moneda_func and costo_total_mov > 0:
            td = db.query(AdmTipoDocumento).filter(AdmTipoDocumento.codigo == "AJ").first()
            td_id = td.id if td else None
            numero = mov.numero
            desc_as = mov.descripcion or f"Ajuste inventario {fecha}"
            periodo = _buscar_periodo_inv(db, fecha)
            asiento = CntAsiento(tipo_documento_id=td_id, documento_numero=numero,
                fecha=fecha, periodo_id=periodo.id, descripcion=desc_as, estado="publicado",
                moneda_id=moneda_func.id, documento_origen_id=mov.id,
                documento_origen_tipo="inv_movimiento", creado_por=actor_id)
            db.add(asiento); db.flush()
            mov.asiento_id = asiento.id
            orden = 1
            for ln in mov.lineas:
                prod = db.get(InvProducto, ln.producto_id)
                if not prod:
                    continue
                cuenta_inv = _resolver_cuenta_inventario_inv(db, prod)
                campo = "cuenta_ajuste_entrada_id" if mov.tipo == "AJUSTE_ENTRADA" else "cuenta_ajuste_salida_id"
                cuenta_ajuste = _resolver_cuenta_ajuste(db, prod, campo)
                if not cuenta_inv or not cuenta_ajuste or ln.costo_total == 0:
                    continue
                costo = ln.costo_total
                if mov.tipo == "AJUSTE_ENTRADA":
                    db.add(CntAsientoLinea(asiento_id=asiento.id, orden=orden, cuenta_id=cuenta_inv.id,
                        descripcion=desc_as, debito=costo, credito=Decimal("0"),
                        debito_funcional=costo, credito_funcional=Decimal("0")))
                    orden += 1
                    db.add(CntAsientoLinea(asiento_id=asiento.id, orden=orden, cuenta_id=cuenta_ajuste.id,
                        descripcion=desc_as, debito=Decimal("0"), credito=costo,
                        debito_funcional=Decimal("0"), credito_funcional=costo))
                else:
                    db.add(CntAsientoLinea(asiento_id=asiento.id, orden=orden, cuenta_id=cuenta_ajuste.id,
                        descripcion=desc_as, debito=costo, credito=Decimal("0"),
                        debito_funcional=costo, credito_funcional=Decimal("0")))
                    orden += 1
                    db.add(CntAsientoLinea(asiento_id=asiento.id, orden=orden, cuenta_id=cuenta_inv.id,
                        descripcion=desc_as, debito=Decimal("0"), credito=costo,
                        debito_funcional=Decimal("0"), credito_funcional=costo))
                orden += 1


def crear_movimiento(db, data, actor: UsuarioActual):
    from datetime import datetime as _dt
    from app.schemas.inventario import MovimientoLineaCreate as MLC

    actor_id = actor.id
    periodo = _buscar_periodo_inv(db, data.fecha)
    es_traslado = data.tipo == "TRASLADO"

    if es_traslado and not data.bodega_destino_id:
        raise HTTPException(status_code=400, detail="El traslado requiere bodega destino")
    if es_traslado and data.bodega_id == data.bodega_destino_id:
        raise HTTPException(status_code=400, detail="Bodega origen y destino deben ser diferentes")

    fecha_dt = _dt.combine(data.fecha, _dt.min.time())
    desc = data.descripcion

    if es_traslado:
        _, numero_tr = _generar_numero(db, "TR")
        mov_sal = InvMovimiento(tipo="TRASLADO_SALIDA", fecha=fecha_dt, periodo_id=periodo.id,
            bodega_id=data.bodega_id, bodega_destino_id=data.bodega_destino_id,
            numero=numero_tr, descripcion=desc, estado="borrador", origen_tipo="traslado_manual", creado_por=actor_id)
        mov_ent = InvMovimiento(tipo="TRASLADO_ENTRADA", fecha=fecha_dt, periodo_id=periodo.id,
            bodega_id=data.bodega_destino_id, bodega_destino_id=data.bodega_id,
            numero=numero_tr, descripcion=desc, estado="borrador", origen_tipo="traslado_manual", creado_por=actor_id)
        db.add(mov_sal); db.add(mov_ent); db.flush()

        for linea in data.lineas:
            pb_orig = db.query(InvProductoBodega).filter(
                InvProductoBodega.producto_id == linea.producto_id,
                InvProductoBodega.bodega_id == data.bodega_id,
            ).first()
            costo_unit = (pb_orig.costo_promedio if pb_orig and pb_orig.costo_promedio > 0 else linea.costo_unitario)

            linea_con_costo = MLC(
                producto_id=linea.producto_id, cantidad=linea.cantidad,
                um_id=linea.um_id, costo_unitario=costo_unit,
            )
            _aplicar_linea_movimiento(db, mov_sal.id, linea_con_costo, data.bodega_id, actor_id)
            _aplicar_linea_movimiento(db, mov_ent.id, linea_con_costo, data.bodega_destino_id, actor_id)

        db.flush()
        db.expire(mov_sal)

        if data.publicar:
            _publicar_movimiento_interno(db, mov_sal, actor_id)

        db.commit()
        db.refresh(mov_sal)
        return obtener_movimiento(db, mov_sal.id)

    # Ajuste entrada / salida
    _, numero_aj = _generar_numero(db, "AJ")
    mov = InvMovimiento(tipo=data.tipo, fecha=fecha_dt, periodo_id=periodo.id,
        bodega_id=data.bodega_id, numero=numero_aj, descripcion=desc,
        estado="borrador", origen_tipo="ajuste_manual", creado_por=actor_id)
    db.add(mov); db.flush()

    for linea in data.lineas:
        _aplicar_linea_movimiento(db, mov.id, linea, data.bodega_id, actor_id)

    db.flush()
    db.expire(mov)

    if data.publicar:
        _publicar_movimiento_interno(db, mov, actor_id)

    db.commit(); db.refresh(mov)
    return obtener_movimiento(db, mov.id)


def publicar_movimiento(db, movimiento_id, actor: UsuarioActual):
    mov = db.get(InvMovimiento, movimiento_id)
    if not mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if mov.estado != "borrador":
        raise HTTPException(status_code=400, detail=f"El movimiento ya está en estado '{mov.estado}'")
    _publicar_movimiento_interno(db, mov, actor.id)
    db.commit(); db.refresh(mov)
    return obtener_movimiento(db, mov.id)


def editar_movimiento(db, movimiento_id: uuid.UUID, data: "MovimientoManualCreate", actor: "UsuarioActual"):
    from app.schemas.inventario import MovimientoManualCreate  # evitar import circular
    mov = db.get(InvMovimiento, movimiento_id)
    if not mov:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if mov.estado != "borrador":
        raise HTTPException(status_code=400, detail="Solo se pueden editar movimientos en borrador")

    from datetime import datetime as _dt

    periodo = _buscar_periodo_inv(db, data.fecha)

    # Determinar tipo real según selección del usuario
    es_traslado = data.tipo == "TRASLADO"

    # Borrar líneas existentes
    db.query(InvMovimientoLinea).filter(InvMovimientoLinea.movimiento_id == mov.id).delete()

    # Actualizar cabecera
    fecha_dt = _dt.combine(data.fecha, _dt.min.time())
    mov.fecha = fecha_dt
    mov.periodo_id = periodo.id
    mov.bodega_id = data.bodega_id
    mov.bodega_destino_id = data.bodega_destino_id
    mov.descripcion = data.descripcion
    db.flush()

    # Si es traslado, también actualizar el movimiento de entrada vinculado
    if es_traslado or mov.tipo in ("TRASLADO_SALIDA", "TRASLADO_ENTRADA"):
        mov_ent = (
            db.query(InvMovimiento)
            .filter(
                InvMovimiento.numero == mov.numero,
                InvMovimiento.tipo == "TRASLADO_ENTRADA",
                InvMovimiento.id != mov.id,
            )
            .first()
        )
        if mov_ent:
            db.query(InvMovimientoLinea).filter(InvMovimientoLinea.movimiento_id == mov_ent.id).delete()
            mov_ent.fecha = fecha_dt
            mov_ent.periodo_id = periodo.id
            mov_ent.bodega_id = data.bodega_destino_id
            mov_ent.bodega_destino_id = data.bodega_id
            mov_ent.descripcion = data.descripcion
            db.flush()

            # Re-crear líneas entrada
            for linea in data.lineas:
                if linea.producto_id and linea.cantidad > 0:
                    linea_con_costo = type(linea)(
                        producto_id=linea.producto_id,
                        cantidad=linea.cantidad,
                        um_id=linea.um_id,
                        costo_unitario=linea.costo_unitario,
                    )
                    _aplicar_linea_movimiento(db, mov_ent.id, linea_con_costo, data.bodega_destino_id, actor.id)

    # Re-crear líneas del movimiento principal
    for linea in data.lineas:
        if linea.producto_id and linea.cantidad > 0:
            _aplicar_linea_movimiento(db, mov.id, linea, data.bodega_id, actor.id)

    db.flush()
    db.expire(mov)

    if data.publicar:
        _publicar_movimiento_interno(db, mov, actor.id)

    db.commit()
    db.refresh(mov)
    return obtener_movimiento(db, mov.id)


def crear_ajuste(db, data, actor: UsuarioActual):
    return crear_movimiento(db, data, actor)

