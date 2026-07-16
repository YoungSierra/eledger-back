"""fac_config_electronica + migra proveedor_tecnologico_nombre

Unifica la configuración del PTH en una sola tabla. Hasta ahora el nombre del
proveedor vivía suelto en adm_configuracion y no había dónde guardar las
credenciales; quedaban en dos sitios distintos.

Revision ID: tt112233ppqq
Revises: ss001122oopp
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "tt112233ppqq"
down_revision = "ss001122oopp"
branch_labels = None
depends_on = None

CLAVE_VIEJA = "proveedor_tecnologico_nombre"


def upgrade():
    op.create_table(
        "fac_config_electronica",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("proveedor", sa.String(30), nullable=False),
        sa.Column("nombre_pth", sa.String(150), nullable=True),
        sa.Column("credenciales", pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ambiente", sa.String(20), nullable=False, server_default="PRUEBAS"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("creado_por", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("modificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modificado_por", pg.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "proveedor IN ('DATAICO','PTH_APIFE','PTH_SIECOM','PTH_FACTUS','DIAN_DIRECTO')",
            name="chk_config_electronica_proveedor",
        ),
        sa.CheckConstraint("ambiente IN ('PRUEBAS','PRODUCCION')", name="chk_config_electronica_ambiente"),
    )

    # Arrastra el nombre del PTH si ya estaba configurado, para no perderlo.
    # Nace inactivo: aún no hay credenciales que lo respalden.
    op.execute(f"""
        INSERT INTO fac_config_electronica (proveedor, nombre_pth, credenciales, ambiente, activo, creado_por)
        SELECT 'DATAICO', c.valor, '{{}}'::jsonb, 'PRUEBAS', false,
               '00000000-0000-0000-0000-000000000001'::uuid
        FROM adm_configuracion c
        WHERE c.clave = '{CLAVE_VIEJA}' AND COALESCE(c.valor, '') <> ''
    """)

    op.execute(f"DELETE FROM adm_configuracion WHERE clave = '{CLAVE_VIEJA}'")


def downgrade():
    op.execute(f"""
        INSERT INTO adm_configuracion (clave, valor, tipo, descripcion)
        SELECT '{CLAVE_VIEJA}', COALESCE(nombre_pth, ''), 'string',
               'Nombre del proveedor tecnológico habilitado DIAN (PTH). Aparece en el pie de la factura electrónica.'
        FROM fac_config_electronica
        LIMIT 1
    """)
    op.execute(f"""
        INSERT INTO adm_configuracion (clave, valor, tipo, descripcion)
        SELECT '{CLAVE_VIEJA}', '', 'string',
               'Nombre del proveedor tecnológico habilitado DIAN (PTH). Aparece en el pie de la factura electrónica.'
        WHERE NOT EXISTS (SELECT 1 FROM adm_configuracion WHERE clave = '{CLAVE_VIEJA}')
    """)
    op.drop_table("fac_config_electronica")
