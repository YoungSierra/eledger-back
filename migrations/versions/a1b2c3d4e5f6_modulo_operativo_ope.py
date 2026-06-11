"""modulo_operativo_ope

Revision ID: a1b2c3d4e5f6
Revises: c30f634ace27
Create Date: 2026-06-03 00:00:00.000000

Crea adm_tercero y todas las tablas del módulo operativo ope_
para Universal Cargo (cotizaciones, operaciones, documentos aéreos).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c30f634ace27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # adm_tercero — tabla base compartida (requerida por Fase 1 también)
    # ------------------------------------------------------------------
    op.create_table(
        'adm_tercero',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nit', sa.String(20), nullable=False),
        sa.Column('digito_verif', sa.String(1), nullable=True),
        sa.Column('razon_social', sa.String(200), nullable=False),
        sa.Column('nombre1', sa.String(100), nullable=True),
        sa.Column('nombre2', sa.String(100), nullable=True),
        sa.Column('apellido1', sa.String(100), nullable=True),
        sa.Column('apellido2', sa.String(100), nullable=True),
        sa.Column('tipo_persona', sa.String(20), nullable=False),
        sa.Column('tipo_tercero', sa.String(50), nullable=False),
        sa.Column('regimen', sa.String(30), nullable=True),
        sa.Column('responsable_iva', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('telefono', sa.String(20), nullable=True),
        sa.Column('direccion', sa.Text(), nullable=True),
        sa.Column('ciudad', sa.String(100), nullable=True),
        sa.Column('departamento', sa.String(100), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("tipo_persona IN ('NATURAL','JURIDICA')", name='chk_tercero_tipo_persona'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nit'),
    )

    # ------------------------------------------------------------------
    # Catálogos operativos
    # ------------------------------------------------------------------
    op.create_table(
        'ope_aerolinea',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('codigo_iata', sa.String(10), nullable=False),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('modalidad', sa.String(20), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.CheckConstraint("modalidad IN ('AEREA','MARITIMA','TERRESTRE')", name='chk_aerolinea_modalidad'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo_iata'),
    )

    op.create_table(
        'ope_aeropuerto',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('codigo_iata', sa.String(10), nullable=False),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('ciudad', sa.String(100), nullable=False),
        sa.Column('pais', sa.String(100), nullable=False),
        sa.Column('modalidad', sa.String(20), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.CheckConstraint("modalidad IN ('AEREA','MARITIMA','TERRESTRE')", name='chk_aeropuerto_modalidad'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo_iata'),
    )

    op.create_table(
        'ope_concepto',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('seccion', sa.String(50), nullable=False),
        sa.Column('tipo_calculo', sa.String(20), nullable=False),
        sa.Column('moneda', sa.String(3), nullable=False),
        sa.Column('cuenta_id', postgresql.UUID(as_uuid=True), nullable=True),  # FK a cnt_cuenta en Fase 1
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "seccion IN ('TRANSPORTE_INTERNACIONAL','GASTOS_ORIGEN','GASTOS_DESTINO','ADUANA','TRANSPORTE_TERRESTRE','ALMACENAMIENTO','SEGURO')",
            name='chk_concepto_seccion',
        ),
        sa.CheckConstraint("tipo_calculo IN ('POR_KG','POR_EMBARQUE','PORCENTAJE')", name='chk_concepto_tipo_calculo'),
        sa.CheckConstraint("moneda IN ('USD','COP')", name='chk_concepto_moneda'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # Cotización
    # ------------------------------------------------------------------
    op.create_table(
        'ope_cotizacion',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('numero', sa.String(20), nullable=False),
        sa.Column('cliente_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('fecha_vigencia', sa.Date(), nullable=False),
        sa.Column('tipo_operacion', sa.String(20), nullable=False),
        sa.Column('modalidad', sa.String(20), nullable=False, server_default='AEREA'),
        sa.Column('origen', sa.String(200), nullable=False),
        sa.Column('destino', sa.String(200), nullable=False),
        sa.Column('aerolinea_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('aeropuerto_origen_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('aeropuerto_destino_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('incoterm', sa.String(10), nullable=True),
        sa.Column('piezas', sa.Integer(), nullable=True),
        sa.Column('peso_kg', sa.Numeric(18, 4), nullable=True),
        sa.Column('valor_mercancia', sa.Numeric(18, 4), nullable=True),
        sa.Column('moneda_mercancia', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('trm', sa.Numeric(18, 4), nullable=True),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('estado', sa.String(20), nullable=False, server_default='BORRADOR'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("tipo_operacion IN ('IMPORTACION','EXPORTACION')", name='chk_cotizacion_tipo_operacion'),
        sa.CheckConstraint("modalidad IN ('AEREA','MARITIMA','TERRESTRE')", name='chk_cotizacion_modalidad'),
        sa.CheckConstraint("estado IN ('BORRADOR','ENVIADA','APROBADA','RECHAZADA','VENCIDA')", name='chk_cotizacion_estado'),
        sa.CheckConstraint("moneda_mercancia IN ('USD','COP')", name='chk_cotizacion_moneda_mercancia'),
        sa.CheckConstraint("incoterm IN ('EXW','FCA','FAS','FOB','CFR','CIF','CPT','CIP','DAP','DPU','DDP')", name='chk_cotizacion_incoterm'),
        sa.ForeignKeyConstraint(['cliente_id'], ['adm_tercero.id']),
        sa.ForeignKeyConstraint(['aerolinea_id'], ['ope_aerolinea.id']),
        sa.ForeignKeyConstraint(['aeropuerto_origen_id'], ['ope_aeropuerto.id']),
        sa.ForeignKeyConstraint(['aeropuerto_destino_id'], ['ope_aeropuerto.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero'),
    )
    op.create_index('idx_cotizacion_cliente', 'ope_cotizacion', ['cliente_id'])
    op.create_index('idx_cotizacion_estado', 'ope_cotizacion', ['estado'])
    op.create_index('idx_cotizacion_fecha', 'ope_cotizacion', ['fecha'])

    op.create_table(
        'ope_cotizacion_linea',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cotizacion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seccion', sa.String(50), nullable=False),
        sa.Column('orden', sa.SmallInteger(), nullable=False),
        sa.Column('concepto_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('descripcion', sa.Text(), nullable=False),
        sa.Column('tipo_calculo', sa.String(20), nullable=False),
        sa.Column('valor_unitario', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('costo_unitario', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('base', sa.Numeric(18, 4), nullable=False, server_default='1'),
        sa.Column('minimo', sa.Numeric(18, 4), nullable=True),
        sa.Column('total_venta', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('total_costo', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('moneda', sa.String(3), nullable=False),
        sa.Column('proveedor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('condiciones_costo', sa.Text(), nullable=True),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "seccion IN ('TRANSPORTE_INTERNACIONAL','GASTOS_ORIGEN','GASTOS_DESTINO','ADUANA','TRANSPORTE_TERRESTRE','ALMACENAMIENTO','SEGURO')",
            name='chk_cot_linea_seccion',
        ),
        sa.CheckConstraint("tipo_calculo IN ('POR_KG','POR_EMBARQUE','PORCENTAJE')", name='chk_cot_linea_tipo_calculo'),
        sa.CheckConstraint("moneda IN ('USD','COP')", name='chk_cot_linea_moneda'),
        sa.ForeignKeyConstraint(['cotizacion_id'], ['ope_cotizacion.id']),
        sa.ForeignKeyConstraint(['concepto_id'], ['ope_concepto.id']),
        sa.ForeignKeyConstraint(['proveedor_id'], ['adm_tercero.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_cot_linea_cotizacion', 'ope_cotizacion_linea', ['cotizacion_id'])

    # ------------------------------------------------------------------
    # Operación (la carpeta — se crea al aprobar cotización)
    # ------------------------------------------------------------------
    op.create_table(
        'ope_operacion',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('numero', sa.String(20), nullable=False),
        sa.Column('cotizacion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fecha_apertura', sa.Date(), nullable=False),
        sa.Column('estado', sa.String(20), nullable=False, server_default='ABIERTA'),
        sa.Column('aerolinea_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('aeropuerto_origen_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('aeropuerto_destino_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('piezas', sa.Integer(), nullable=True),
        sa.Column('peso_kg', sa.Numeric(18, 4), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("estado IN ('ABIERTA','EN_CURSO','CERRADA','CANCELADA')", name='chk_operacion_estado'),
        sa.ForeignKeyConstraint(['cotizacion_id'], ['ope_cotizacion.id']),
        sa.ForeignKeyConstraint(['aerolinea_id'], ['ope_aerolinea.id']),
        sa.ForeignKeyConstraint(['aeropuerto_origen_id'], ['ope_aeropuerto.id']),
        sa.ForeignKeyConstraint(['aeropuerto_destino_id'], ['ope_aeropuerto.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero'),
        sa.UniqueConstraint('cotizacion_id'),
    )
    op.create_index('idx_operacion_estado', 'ope_operacion', ['estado'])
    op.create_index('idx_operacion_cotizacion', 'ope_operacion', ['cotizacion_id'])

    # ------------------------------------------------------------------
    # HAWB
    # ------------------------------------------------------------------
    op.create_table(
        'ope_hawb',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operacion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('numero_hawb', sa.String(50), nullable=False),
        sa.Column('shipper_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('consignee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aeropuerto_origen_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('aeropuerto_destino_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('aerolinea_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vuelo', sa.String(20), nullable=True),
        sa.Column('fecha_vuelo', sa.Date(), nullable=True),
        sa.Column('piezas', sa.Integer(), nullable=True),
        sa.Column('peso_bruto_kg', sa.Numeric(18, 4), nullable=True),
        sa.Column('peso_cargable_kg', sa.Numeric(18, 4), nullable=True),
        sa.Column('descripcion_mercancia', sa.Text(), nullable=True),
        sa.Column('dimensiones', sa.Text(), nullable=True),
        sa.Column('trm', sa.Numeric(18, 4), nullable=True),
        sa.Column('estado', sa.String(20), nullable=False, server_default='BORRADOR'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("estado IN ('BORRADOR','EMITIDA','ANULADA')", name='chk_hawb_estado'),
        sa.ForeignKeyConstraint(['operacion_id'], ['ope_operacion.id']),
        sa.ForeignKeyConstraint(['shipper_id'], ['adm_tercero.id']),
        sa.ForeignKeyConstraint(['consignee_id'], ['adm_tercero.id']),
        sa.ForeignKeyConstraint(['aeropuerto_origen_id'], ['ope_aeropuerto.id']),
        sa.ForeignKeyConstraint(['aeropuerto_destino_id'], ['ope_aeropuerto.id']),
        sa.ForeignKeyConstraint(['aerolinea_id'], ['ope_aerolinea.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_hawb_operacion', 'ope_hawb', ['operacion_id'])

    # ------------------------------------------------------------------
    # MAWB
    # ------------------------------------------------------------------
    op.create_table(
        'ope_mawb',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operacion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('numero_mawb', sa.String(50), nullable=False),
        sa.Column('aerolinea_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('aeropuerto_origen_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('aeropuerto_destino_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vuelo', sa.String(20), nullable=True),
        sa.Column('fecha_vuelo', sa.Date(), nullable=True),
        sa.Column('piezas', sa.Integer(), nullable=True),
        sa.Column('peso_bruto_kg', sa.Numeric(18, 4), nullable=True),
        sa.Column('peso_cargable_kg', sa.Numeric(18, 4), nullable=True),
        sa.Column('descripcion_mercancia', sa.Text(), nullable=True),
        sa.Column('flete_total', sa.Numeric(18, 4), nullable=True),
        sa.Column('moneda_flete', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('estado', sa.String(20), nullable=False, server_default='BORRADOR'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modificado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('modificado_por', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("estado IN ('BORRADOR','EMITIDA','ANULADA')", name='chk_mawb_estado'),
        sa.CheckConstraint("moneda_flete IN ('USD','COP')", name='chk_mawb_moneda_flete'),
        sa.ForeignKeyConstraint(['operacion_id'], ['ope_operacion.id']),
        sa.ForeignKeyConstraint(['aerolinea_id'], ['ope_aerolinea.id']),
        sa.ForeignKeyConstraint(['aeropuerto_origen_id'], ['ope_aeropuerto.id']),
        sa.ForeignKeyConstraint(['aeropuerto_destino_id'], ['ope_aeropuerto.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_mawb_operacion', 'ope_mawb', ['operacion_id'])

    # ------------------------------------------------------------------
    # Manifiesto
    # ------------------------------------------------------------------
    op.create_table(
        'ope_manifiesto',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operacion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mawb_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aerolinea_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('estado', sa.String(20), nullable=False, server_default='BORRADOR'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("estado IN ('BORRADOR','EMITIDA','ANULADA')", name='chk_manifiesto_estado'),
        sa.ForeignKeyConstraint(['operacion_id'], ['ope_operacion.id']),
        sa.ForeignKeyConstraint(['mawb_id'], ['ope_mawb.id']),
        sa.ForeignKeyConstraint(['aerolinea_id'], ['ope_aerolinea.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_manifiesto_operacion', 'ope_manifiesto', ['operacion_id'])

    op.create_table(
        'ope_manifiesto_linea',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('manifiesto_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hawb_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exportador_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('importador_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('piezas', sa.Integer(), nullable=True),
        sa.Column('peso_kg', sa.Numeric(18, 4), nullable=True),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['manifiesto_id'], ['ope_manifiesto.id']),
        sa.ForeignKeyConstraint(['hawb_id'], ['ope_hawb.id']),
        sa.ForeignKeyConstraint(['exportador_id'], ['adm_tercero.id']),
        sa.ForeignKeyConstraint(['importador_id'], ['adm_tercero.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ------------------------------------------------------------------
    # Bitácora y documentos requeridos
    # ------------------------------------------------------------------
    op.create_table(
        'ope_evento',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operacion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fecha_hora', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('usuario_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tipo', sa.String(30), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=False),
        sa.Column('notificado_cliente', sa.Boolean(), nullable=False, server_default='false'),
        sa.CheckConstraint(
            "tipo IN ('STATUS','DOCUMENTO_RECIBIDO','NOTA','RESERVA','APERTURA','CIERRE')",
            name='chk_evento_tipo',
        ),
        sa.ForeignKeyConstraint(['operacion_id'], ['ope_operacion.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['adm_usuario.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_evento_operacion', 'ope_evento', ['operacion_id'])
    op.create_index('idx_evento_fecha', 'ope_evento', ['fecha_hora'])

    op.create_table(
        'ope_documento',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operacion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tipo', sa.String(30), nullable=False),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('estado', sa.String(20), nullable=False, server_default='PENDIENTE'),
        sa.Column('fecha_recepcion', sa.Date(), nullable=True),
        sa.Column('archivo', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('creado_por', postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('FACTURA_COMERCIAL','LISTA_EMPAQUE','CERTIFICADO_ORIGEN','OTRO')",
            name='chk_documento_tipo',
        ),
        sa.CheckConstraint("estado IN ('PENDIENTE','RECIBIDO','APROBADO')", name='chk_documento_estado'),
        sa.ForeignKeyConstraint(['operacion_id'], ['ope_operacion.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_documento_operacion', 'ope_documento', ['operacion_id'])


def downgrade() -> None:
    op.drop_index('idx_documento_operacion', table_name='ope_documento')
    op.drop_table('ope_documento')
    op.drop_index('idx_evento_fecha', table_name='ope_evento')
    op.drop_index('idx_evento_operacion', table_name='ope_evento')
    op.drop_table('ope_evento')
    op.drop_table('ope_manifiesto_linea')
    op.drop_index('idx_manifiesto_operacion', table_name='ope_manifiesto')
    op.drop_table('ope_manifiesto')
    op.drop_index('idx_mawb_operacion', table_name='ope_mawb')
    op.drop_table('ope_mawb')
    op.drop_index('idx_hawb_operacion', table_name='ope_hawb')
    op.drop_table('ope_hawb')
    op.drop_index('idx_operacion_cotizacion', table_name='ope_operacion')
    op.drop_index('idx_operacion_estado', table_name='ope_operacion')
    op.drop_table('ope_operacion')
    op.drop_index('idx_cot_linea_cotizacion', table_name='ope_cotizacion_linea')
    op.drop_table('ope_cotizacion_linea')
    op.drop_index('idx_cotizacion_fecha', table_name='ope_cotizacion')
    op.drop_index('idx_cotizacion_estado', table_name='ope_cotizacion')
    op.drop_index('idx_cotizacion_cliente', table_name='ope_cotizacion')
    op.drop_table('ope_cotizacion')
    op.drop_table('ope_concepto')
    op.drop_table('ope_aeropuerto')
    op.drop_table('ope_aerolinea')
    op.drop_table('adm_tercero')
