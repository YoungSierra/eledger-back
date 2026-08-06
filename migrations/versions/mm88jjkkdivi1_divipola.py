"""Catálogo DIVIPOLA (municipios DANE) + municipio_codigo en empresa y terceros

La facturación electrónica identifica al emisor y al adquiriente con el código
DANE de 5 dígitos del municipio, pero hasta ahora ciudad/departamento eran texto
libre. Se agrega el catálogo y la referencia; ciudad/departamento se conservan y
quedan sincronizados desde el catálogo para no romper impresiones ni reportes.

El backfill intenta emparejar por nombre normalizado (sin tildes, sin
mayúsculas). Lo que no empareje queda en NULL y se corrige desde la pantalla.

Revision ID: mm88jjkk0001
Revises: ll77iijj0001
"""
from alembic import op
import sqlalchemy as sa

revision = "mm88jjkk0001"
down_revision = "ll77iijj0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adm_municipio",
        sa.Column("codigo", sa.String(length=5), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("depto_codigo", sa.String(length=2), nullable=False),
        sa.Column("depto_nombre", sa.String(length=100), nullable=False),
    )
    op.create_index("ix_adm_municipio_depto_codigo", "adm_municipio", ["depto_codigo"])

    for tabla in ("adm_empresa", "adm_tercero"):
        op.add_column(tabla, sa.Column("municipio_codigo", sa.String(length=5), nullable=True))
        op.create_foreign_key(
            f"fk_{tabla}_municipio", tabla, "adm_municipio", ["municipio_codigo"], ["codigo"],
        )

    # El backfill real corre en el seed (`seed_municipios.py`), que primero carga
    # el catálogo y después empareja: aquí la tabla todavía está vacía.


def downgrade() -> None:
    for tabla in ("adm_empresa", "adm_tercero"):
        op.drop_constraint(f"fk_{tabla}_municipio", tabla, type_="foreignkey")
        op.drop_column(tabla, "municipio_codigo")
    op.drop_index("ix_adm_municipio_depto_codigo", table_name="adm_municipio")
    op.drop_table("adm_municipio")
