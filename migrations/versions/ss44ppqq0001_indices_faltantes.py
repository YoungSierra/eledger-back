"""Crea los índices que los modelos declaran y nunca se emitieron

Cinco columnas quedaron con `index=True` en el modelo, pero la migración que las
agregó creó la columna y no el índice. El ORM no lo nota —consulta igual— así
que pasó desapercibido: la diferencia solo aparece comparando modelo contra BD.

Todas son claves foráneas por las que sí se filtra. `fac_factura.cotizacion_id`
en particular lo consulta el estado de facturación de cada cotización, que corre
una vez por cotización al abrir una operación. Sin índice es recorrido completo
de tabla; hoy no se nota, con volumen sí.

Se usa IF NOT EXISTS porque alguno podría haberse creado a mano.

Revision ID: ss44ppqq0001
Revises: rr33oopp0001
"""
from alembic import op

revision = "ss44ppqq0001"
down_revision = "rr33oopp0001"
branch_labels = None
depends_on = None

INDICES = [
    ("ix_fac_factura_cotizacion_id", "fac_factura", "cotizacion_id"),
    ("ix_fac_factura_linea_cotizacion_linea_id", "fac_factura_linea", "cotizacion_linea_id"),
    ("ix_ope_cotizacion_operacion_id", "ope_cotizacion", "operacion_id"),
    ("ix_ope_evento_hawb_id", "ope_evento", "hawb_id"),
    ("ix_ope_hawb_cotizacion_id", "ope_hawb", "cotizacion_id"),
]


def upgrade() -> None:
    for nombre, tabla, columna in INDICES:
        op.execute(f'CREATE INDEX IF NOT EXISTS "{nombre}" ON "{tabla}" ("{columna}")')


def downgrade() -> None:
    for nombre, _, _ in INDICES:
        op.execute(f'DROP INDEX IF EXISTS "{nombre}"')
