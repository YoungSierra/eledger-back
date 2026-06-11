"""CxP — Cuentas por pagar: tablas y menú

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e0f1a2b3c4d5'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cxp_parametro_contable',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cuenta_proveedores_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['cuenta_proveedores_id'], ['cnt_cuenta.id'], name='fk_cxp_param_proveedores'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'cxp_documento',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('numero', sa.String(30), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('numero_proveedor', sa.String(50), nullable=True),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('fecha_vencimiento', sa.Date(), nullable=True),
        sa.Column('periodo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tercero_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('moneda_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trm', sa.Numeric(18, 6), nullable=True),
        sa.Column('subtotal', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total_iva', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total_retenciones', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('saldo', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('estado', sa.String(20), nullable=False, server_default='borrador'),
        sa.Column('asiento_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asiento_modificado_manual', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('origen_modulo', sa.String(50), nullable=True),
        sa.Column('origen_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('documento_origen_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("tipo IN ('FACTURA','COMPROBANTE','NOTA_CREDITO','NOTA_DEBITO','ANTICIPO')", name='chk_cxp_tipo'),
        sa.CheckConstraint("estado IN ('borrador','contabilizado','anulado')", name='chk_cxp_estado'),
        sa.CheckConstraint('saldo >= 0', name='chk_cxp_saldo'),
        sa.CheckConstraint('total >= 0', name='chk_cxp_total'),
        sa.CheckConstraint("tipo NOT IN ('FACTURA','NOTA_DEBITO') OR fecha_vencimiento IS NOT NULL", name='chk_cxp_vencimiento'),
        sa.ForeignKeyConstraint(['periodo_id'], ['cnt_periodo.id'], name='fk_cxp_periodo'),
        sa.ForeignKeyConstraint(['tercero_id'], ['adm_tercero.id'], name='fk_cxp_tercero'),
        sa.ForeignKeyConstraint(['moneda_id'], ['adm_moneda.id'], name='fk_cxp_moneda'),
        sa.ForeignKeyConstraint(['asiento_id'], ['cnt_asiento.id'], name='fk_cxp_asiento'),
        sa.ForeignKeyConstraint(['documento_origen_id'], ['cxp_documento.id'], name='fk_cxp_doc_origen'),
        sa.UniqueConstraint('numero', name='uq_cxp_numero'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_cxp_tercero', 'cxp_documento', ['tercero_id'])
    op.create_index('idx_cxp_estado', 'cxp_documento', ['estado'])
    op.create_index('idx_cxp_fecha', 'cxp_documento', ['fecha'])
    op.create_index('idx_cxp_tipo', 'cxp_documento', ['tipo'])

    op.create_table(
        'cxp_documento_linea',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('documento_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('orden', sa.SmallInteger(), nullable=False, server_default='1'),
        sa.Column('descripcion', sa.String(300), nullable=False),
        sa.Column('concepto_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cuenta_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subtotal', sa.Numeric(18, 4), nullable=False),
        sa.Column('iva_pct', sa.Numeric(8, 4), nullable=False, server_default='0'),
        sa.Column('total_iva', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(18, 4), nullable=False),
        sa.Column('centro_costo_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('iva_tipo', sa.String(20), nullable=False, server_default='NINGUNO'),
        sa.Column('cuenta_iva_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint('concepto_id IS NOT NULL OR cuenta_id IS NOT NULL', name='chk_cxp_linea_cuenta'),
        sa.CheckConstraint('subtotal > 0', name='chk_cxp_linea_subtotal'),
        sa.CheckConstraint("iva_tipo IN ('GRAVADO_19','GRAVADO_5','EXCLUIDO','EXENTO','INC','NINGUNO')", name='chk_cxp_linea_iva_tipo'),
        sa.ForeignKeyConstraint(['documento_id'], ['cxp_documento.id'], name='fk_cxp_linea_doc', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['concepto_id'], ['adm_concepto.id'], name='fk_cxp_linea_concepto'),
        sa.ForeignKeyConstraint(['cuenta_id'], ['cnt_cuenta.id'], name='fk_cxp_linea_cuenta_dir'),
        sa.ForeignKeyConstraint(['centro_costo_id'], ['cnt_centro_costo.id'], name='fk_cxp_linea_cc'),
        sa.ForeignKeyConstraint(['cuenta_iva_id'], ['cnt_cuenta.id'], name='fk_cxp_linea_iva'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_cxp_linea_documento', 'cxp_documento_linea', ['documento_id'])

    op.create_table(
        'cxp_linea_retencion',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('linea_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('descripcion', sa.String(100), nullable=False),
        sa.Column('base', sa.Numeric(18, 4), nullable=False),
        sa.Column('porcentaje', sa.Numeric(8, 4), nullable=False),
        sa.Column('valor', sa.Numeric(18, 4), nullable=False),
        sa.Column('cuenta_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("tipo IN ('RETEFUENTE','RETEICA','RETEIVA')", name='chk_cxp_lret_tipo'),
        sa.ForeignKeyConstraint(['linea_id'], ['cxp_documento_linea.id'], name='fk_cxp_lret_linea', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cuenta_id'], ['cnt_cuenta.id'], name='fk_cxp_lret_cuenta'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'cxp_aplicacion',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('documento_credito_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('documento_debito_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('valor', sa.Numeric(18, 4), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint('valor > 0', name='chk_cxp_app_valor'),
        sa.CheckConstraint('documento_credito_id <> documento_debito_id', name='chk_cxp_app_distintos'),
        sa.ForeignKeyConstraint(['documento_credito_id'], ['cxp_documento.id'], name='fk_cxp_app_credito'),
        sa.ForeignKeyConstraint(['documento_debito_id'], ['cxp_documento.id'], name='fk_cxp_app_debito'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_cxp_app_credito', 'cxp_aplicacion', ['documento_credito_id'])
    op.create_index('idx_cxp_app_debito', 'cxp_aplicacion', ['documento_debito_id'])

    op.execute("INSERT INTO cxp_parametro_contable (id) VALUES (gen_random_uuid())")

    # Marcar facturas_cxp como implementada en el menú
    op.execute("""
        UPDATE adm_opcion SET implementada = true
        WHERE codigo = 'facturas_cxp'
    """)
    # Agregar opción Parámetros CxP si no existe
    op.execute("""
        INSERT INTO adm_opcion (id, modulo_id, codigo, nombre, ruta, orden, implementada, activo)
        SELECT gen_random_uuid(), m.id, 'parametros_cxp', 'Parámetros CxP',
               '/dashboard/administracion/parametros-cxp', 10, true, true
        FROM adm_modulo m
        WHERE m.codigo = 'administracion'
          AND NOT EXISTS (
              SELECT 1 FROM adm_opcion WHERE codigo = 'parametros_cxp'
          )
    """)
    # Dar acceso al superadmin a las nuevas opciones
    op.execute("""
        INSERT INTO adm_permiso_opcion (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_autorizar)
        SELECT gen_random_uuid(), r.id, o.id, true, true, true, true, true
        FROM adm_rol r, adm_opcion o
        WHERE r.nombre = 'superadmin'
          AND o.codigo IN ('facturas_cxp', 'parametros_cxp')
          AND NOT EXISTS (
              SELECT 1 FROM adm_permiso_opcion p
              WHERE p.rol_id = r.id AND p.opcion_id = o.id
          )
    """)


def downgrade():
    op.drop_index('idx_cxp_app_debito', 'cxp_aplicacion')
    op.drop_index('idx_cxp_app_credito', 'cxp_aplicacion')
    op.drop_table('cxp_aplicacion')
    op.drop_table('cxp_linea_retencion')
    op.drop_index('idx_cxp_linea_documento', 'cxp_documento_linea')
    op.drop_table('cxp_documento_linea')
    op.drop_index('idx_cxp_tipo', 'cxp_documento')
    op.drop_index('idx_cxp_fecha', 'cxp_documento')
    op.drop_index('idx_cxp_estado', 'cxp_documento')
    op.drop_index('idx_cxp_tercero', 'cxp_documento')
    op.drop_table('cxp_documento')
    op.drop_table('cxp_parametro_contable')
