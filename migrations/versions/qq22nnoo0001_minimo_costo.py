"""Mínimo de costo separado del mínimo de venta

En la reunión se acordó un mínimo único aplicando a los dos lados, pero al verlo
en pantalla el cliente pidió separarlos: el mínimo que nos cobra el proveedor no
tiene por qué ser el que le cobramos al cliente.

`minimo` pasa a ser el de venta y entra `minimo_costo`. No hay backfill de
`minimo` hacia `minimo_costo`: copiar el mínimo de venta al costo inflaría el
costo de las líneas existentes y falsearía el margen histórico. Las líneas
actuales quedan sin mínimo de costo, que es como se cotizaron.

Revision ID: qq22nnoo0001
Revises: pp11mmnn0001
"""
from alembic import op
import sqlalchemy as sa

revision = "qq22nnoo0001"
down_revision = "pp11mmnn0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ope_cotizacion_linea", sa.Column("minimo_costo", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("ope_cotizacion_linea", "minimo_costo")
