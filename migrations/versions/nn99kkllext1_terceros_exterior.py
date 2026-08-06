"""Catálogo de países ISO + pais_codigo y tipo_documento_dian en terceros

Necesario para facturar al exterior: la DIAN identifica al adquiriente
extranjero con el código ISO de 2 letras y con un tipo de documento que no es
NIT ni cédula (50 = NIT otro país, 42 = documento extranjero…). Antes el tipo se
deducía de `tipo_persona` y solo producía 13 o 31, y el país era texto libre.

Revision ID: nn99kkll0001
Revises: mm88jjkk0001
"""
from alembic import op
import sqlalchemy as sa

revision = "nn99kkll0001"
down_revision = "mm88jjkk0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adm_pais",
        sa.Column("codigo", sa.String(length=2), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
    )
    op.add_column("adm_tercero", sa.Column("pais_codigo", sa.String(length=2), nullable=True))
    op.add_column("adm_tercero", sa.Column("tipo_documento_dian", sa.String(length=2), nullable=True))
    op.create_foreign_key("fk_adm_tercero_pais", "adm_tercero", "adm_pais", ["pais_codigo"], ["codigo"])

    # El catálogo y el backfill corren en el seed (`seed_paises.py`): aquí la
    # tabla todavía está vacía y la FK no dejaría asignar códigos.


def downgrade() -> None:
    op.drop_constraint("fk_adm_tercero_pais", "adm_tercero", type_="foreignkey")
    op.drop_column("adm_tercero", "tipo_documento_dian")
    op.drop_column("adm_tercero", "pais_codigo")
    op.drop_table("adm_pais")
