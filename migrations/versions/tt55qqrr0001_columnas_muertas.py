"""Elimina las columnas `eliminado` que quedaron muertas

Restos de cuando el borrado lógico pasó a llamarse `activo`. Ningún modelo las
declara y ninguna consulta las usa; verificado antes de borrar: todas las filas
en `false` (adm_concepto 10, ban_chequera 1) y cero referencias en el código.

Se borran, y no se dejan "por si acaso", porque una columna que existe y no
significa nada es una trampa: junto a `activo` invita a filtrar por ella y a
obtener un resultado silenciosamente incorrecto. Además ese ruido es el que
escondió durante meses cinco índices declarados y nunca creados — cuando la
comparación modelo/BD tiene decenas de diferencias que uno aprende a ignorar,
deja de servir para detectar las que importan.

La reversión es exacta: el valor era uniforme, así que recrear la columna con su
default reconstruye el estado anterior.

Revision ID: tt55qqrr0001
Revises: ss44ppqq0001
"""
from alembic import op
import sqlalchemy as sa

revision = "tt55qqrr0001"
down_revision = "ss44ppqq0001"
branch_labels = None
depends_on = None

TABLAS = ("adm_concepto", "ban_chequera")


def upgrade() -> None:
    for t in TABLAS:
        op.drop_column(t, "eliminado")


def downgrade() -> None:
    for t in TABLAS:
        op.add_column(
            t,
            sa.Column("eliminado", sa.Boolean(), nullable=False,
                      server_default=sa.text("false")),
        )
