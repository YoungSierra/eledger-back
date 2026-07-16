"""compras y movimientos de inventario

Revision ID: nn556677iijj
Revises: mm445566hhii
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "nn556677iijj"
down_revision = "mm445566hhii"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Inventario: stock y movimientos ──────────────────────────────────────
    op.create_table(
        "inv_producto_bodega",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("producto_id", sa.UUID(), nullable=False),
        sa.Column("bodega_id", sa.UUID(), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("costo_promedio", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["producto_id"], ["inv_producto.id"]),
        sa.ForeignKeyConstraint(["bodega_id"], ["inv_bodega.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("producto_id", "bodega_id", name="uq_producto_bodega"),
        sa.CheckConstraint("cantidad >= 0", name="chk_stock_no_negativo"),
    )

    op.create_table(
        "inv_movimiento",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(25), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=False), nullable=False),
        sa.Column("periodo_id", sa.UUID(), nullable=False),
        sa.Column("bodega_id", sa.UUID(), nullable=False),
        sa.Column("bodega_destino_id", sa.UUID(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="confirmado"),
        sa.Column("origen_tipo", sa.String(50), nullable=True),
        sa.Column("origen_id", sa.UUID(), nullable=True),
        sa.Column("asiento_id", sa.UUID(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("creado_por", sa.UUID(), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["periodo_id"], ["cnt_periodo.id"]),
        sa.ForeignKeyConstraint(["bodega_id"], ["inv_bodega.id"]),
        sa.ForeignKeyConstraint(["bodega_destino_id"], ["inv_bodega.id"]),
        sa.ForeignKeyConstraint(["asiento_id"], ["cnt_asiento.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "tipo IN ('ENTRADA_COMPRA','SALIDA_VENTA','TRASLADO_SALIDA','TRASLADO_ENTRADA',"
            "'AJUSTE_ENTRADA','AJUSTE_SALIDA','DEVOLUCION_CLIENTE','DEVOLUCION_PROVEEDOR',"
            "'ENTRADA_PRODUCCION','SALIDA_PRODUCCION')",
            name="chk_movimiento_tipo",
        ),
    )
    op.create_index("idx_movimiento_tipo", "inv_movimiento", ["tipo"])
    op.create_index("idx_movimiento_fecha", "inv_movimiento", ["fecha"])
    op.create_index("idx_movimiento_origen", "inv_movimiento", ["origen_tipo", "origen_id"])

    op.create_table(
        "inv_movimiento_linea",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("movimiento_id", sa.UUID(), nullable=False),
        sa.Column("producto_id", sa.UUID(), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("um_id", sa.UUID(), nullable=False),
        sa.Column("cantidad_base", sa.Numeric(18, 4), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("costo_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["movimiento_id"], ["inv_movimiento.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["inv_producto.id"]),
        sa.ForeignKeyConstraint(["um_id"], ["inv_unidad_medida.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("cantidad > 0", name="chk_movlinea_cantidad"),
    )
    op.create_index("idx_movlinea_movimiento", "inv_movimiento_linea", ["movimiento_id"])
    op.create_index("idx_movlinea_producto", "inv_movimiento_linea", ["producto_id"])

    # ── Compras: OC y recepciones ─────────────────────────────────────────────
    op.create_table(
        "com_orden_compra",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("numero", sa.String(30), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("fecha_entrega_esperada", sa.Date(), nullable=True),
        sa.Column("periodo_id", sa.UUID(), nullable=False),
        sa.Column("proveedor_id", sa.UUID(), nullable=False),
        sa.Column("moneda_id", sa.UUID(), nullable=False),
        sa.Column("trm", sa.Numeric(18, 6), nullable=True),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_iva", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="borrador"),
        sa.Column("aprobado_por", sa.UUID(), nullable=True),
        sa.Column("aprobado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("creado_por", sa.UUID(), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["periodo_id"], ["cnt_periodo.id"]),
        sa.ForeignKeyConstraint(["proveedor_id"], ["adm_tercero.id"]),
        sa.ForeignKeyConstraint(["moneda_id"], ["adm_moneda.id"]),
        sa.ForeignKeyConstraint(["aprobado_por"], ["adm_usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero", name="uq_oc_numero"),
        sa.CheckConstraint(
            "estado IN ('borrador','aprobada','en_proceso','recibida_total','anulada')",
            name="chk_oc_estado",
        ),
    )
    op.create_index("idx_oc_proveedor", "com_orden_compra", ["proveedor_id"])
    op.create_index("idx_oc_fecha", "com_orden_compra", ["fecha"])
    op.create_index("idx_oc_estado", "com_orden_compra", ["estado"])

    op.create_table(
        "com_oc_linea",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("oc_id", sa.UUID(), nullable=False),
        sa.Column("producto_id", sa.UUID(), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("um_id", sa.UUID(), nullable=False),
        sa.Column("cantidad_base", sa.Numeric(18, 4), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(18, 4), nullable=False),
        sa.Column("descuento_pct", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False),
        sa.Column("iva_pct", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("total_iva", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False),
        sa.Column("cantidad_recibida", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["oc_id"], ["com_orden_compra.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["inv_producto.id"]),
        sa.ForeignKeyConstraint(["um_id"], ["inv_unidad_medida.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("cantidad > 0", name="chk_oc_cantidad"),
    )

    op.create_table(
        "com_recepcion",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("numero", sa.String(30), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("periodo_id", sa.UUID(), nullable=False),
        sa.Column("oc_id", sa.UUID(), nullable=False),
        sa.Column("bodega_id", sa.UUID(), nullable=False),
        sa.Column("proveedor_id", sa.UUID(), nullable=False),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="borrador"),
        sa.Column("movimiento_id", sa.UUID(), nullable=True),
        sa.Column("asiento_id", sa.UUID(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("creado_por", sa.UUID(), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["periodo_id"], ["cnt_periodo.id"]),
        sa.ForeignKeyConstraint(["oc_id"], ["com_orden_compra.id"]),
        sa.ForeignKeyConstraint(["bodega_id"], ["inv_bodega.id"]),
        sa.ForeignKeyConstraint(["proveedor_id"], ["adm_tercero.id"]),
        sa.ForeignKeyConstraint(["movimiento_id"], ["inv_movimiento.id"]),
        sa.ForeignKeyConstraint(["asiento_id"], ["cnt_asiento.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero", name="uq_recepcion_numero"),
        sa.CheckConstraint(
            "estado IN ('borrador','confirmada','anulada')",
            name="chk_recepcion_estado",
        ),
    )
    op.create_index("idx_recepcion_oc", "com_recepcion", ["oc_id"])
    op.create_index("idx_recepcion_fecha", "com_recepcion", ["fecha"])

    op.create_table(
        "com_recepcion_linea",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recepcion_id", sa.UUID(), nullable=False),
        sa.Column("oc_linea_id", sa.UUID(), nullable=False),
        sa.Column("producto_id", sa.UUID(), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("um_id", sa.UUID(), nullable=False),
        sa.Column("cantidad_base", sa.Numeric(18, 4), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(18, 4), nullable=False),
        sa.ForeignKeyConstraint(["recepcion_id"], ["com_recepcion.id"]),
        sa.ForeignKeyConstraint(["oc_linea_id"], ["com_oc_linea.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["inv_producto.id"]),
        sa.ForeignKeyConstraint(["um_id"], ["inv_unidad_medida.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("cantidad > 0", name="chk_recep_cantidad"),
    )

    # ── Consecutivo RECP (Recepción de mercancía) ─────────────────────────────
    op.execute("""
        INSERT INTO adm_tipo_documento (id, codigo, nombre, modulo, activo)
        VALUES (gen_random_uuid(), 'RECP', 'Recepción de mercancía', 'compras', TRUE)
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO adm_consecutivo (id, tipo_documento_id, prefijo, numero_actual, numero_inicio, longitud_minima, activo)
        SELECT gen_random_uuid(), td.id, 'RECP', 0, 1, 5, TRUE
        FROM adm_tipo_documento td
        WHERE td.codigo = 'RECP'
        ON CONFLICT DO NOTHING
    """)

    # ── Menú: activar compras ─────────────────────────────────────────────────
    op.execute("""
        UPDATE adm_opcion SET implementada = TRUE
        WHERE codigo IN ('ordenes', 'recepciones')
          AND modulo_id = (SELECT id FROM adm_modulo WHERE codigo = 'compras')
    """)


def downgrade() -> None:
    op.execute("UPDATE adm_opcion SET implementada = FALSE WHERE codigo IN ('ordenes','recepciones')")
    op.execute("DELETE FROM adm_consecutivo WHERE tipo_documento_id = (SELECT id FROM adm_tipo_documento WHERE codigo='RECP')")
    op.execute("DELETE FROM adm_tipo_documento WHERE codigo = 'RECP'")
    op.drop_table("com_recepcion_linea")
    op.drop_table("com_recepcion")
    op.drop_table("com_oc_linea")
    op.drop_table("com_orden_compra")
    op.drop_index("idx_movlinea_producto", "inv_movimiento_linea")
    op.drop_index("idx_movlinea_movimiento", "inv_movimiento_linea")
    op.drop_table("inv_movimiento_linea")
    op.drop_index("idx_movimiento_origen", "inv_movimiento")
    op.drop_index("idx_movimiento_fecha", "inv_movimiento")
    op.drop_index("idx_movimiento_tipo", "inv_movimiento")
    op.drop_table("inv_movimiento")
    op.drop_table("inv_producto_bodega")
