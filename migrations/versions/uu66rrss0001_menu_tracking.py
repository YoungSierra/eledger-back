"""Opción de menú: Rastreo de embarques

Va en la posición 3, justo después de Operaciones y antes de los catálogos,
porque es pantalla de uso diario: hacen seguimiento dos o tres veces por semana.
Los catálogos se corren una posición.

Los permisos se copian de la opción `operaciones`: quien ya ve las operaciones
debe poder rastrearlas. Replicarlos en vez de fijarlos a dedo evita que se
desincronicen con los roles reales de esta instalación.

Recordatorio: el menú se arma SOLO desde adm_permiso_opcion.puede_ver. El
superadmin no salta esa validación, así que sin fila de permiso la opción no
aparece para nadie.

Revision ID: uu66rrss0001
Revises: tt55qqrr0001
"""
from alembic import op
import sqlalchemy as sa

revision = "uu66rrss0001"
down_revision = "tt55qqrr0001"
branch_labels = None
depends_on = None

CODIGO = "tracking"
RUTA = "/dashboard/operaciones/tracking"


def upgrade() -> None:
    conn = op.get_bind()
    modulo = conn.execute(sa.text(
        "SELECT id FROM adm_modulo WHERE codigo ILIKE '%ope%' LIMIT 1"
    )).scalar()
    if not modulo:
        return

    # Hueco en la posición 3
    conn.execute(sa.text(
        "UPDATE adm_opcion SET orden = orden + 1 "
        "WHERE modulo_id = :m AND orden >= 3"
    ), {"m": modulo})

    conn.execute(sa.text("""
        INSERT INTO adm_opcion (id, modulo_id, codigo, nombre, ruta, orden, implementada, activo)
        VALUES (gen_random_uuid(), :m, :c, 'Rastreo de embarques', :r, 3, true, true)
        ON CONFLICT DO NOTHING
    """), {"m": modulo, "c": CODIGO, "r": RUTA})

    # Mismos permisos que tenga la opción `operaciones`, pero solo de consulta.
    conn.execute(sa.text("""
        INSERT INTO adm_permiso_opcion
            (id, rol_id, opcion_id, puede_ver, puede_crear, puede_editar,
             puede_eliminar, puede_imprimir, puede_autorizar)
        SELECT gen_random_uuid(), p.rol_id, nueva.id,
               p.puede_ver, false, false, false, p.puede_imprimir, false
        FROM adm_permiso_opcion p
        JOIN adm_opcion base  ON base.id = p.opcion_id
        JOIN adm_opcion nueva ON nueva.codigo = :c AND nueva.modulo_id = :m
        WHERE base.codigo = 'operaciones' AND base.modulo_id = :m
        ON CONFLICT DO NOTHING
    """), {"m": modulo, "c": CODIGO})


def downgrade() -> None:
    conn = op.get_bind()
    modulo = conn.execute(sa.text(
        "SELECT id FROM adm_modulo WHERE codigo ILIKE '%ope%' LIMIT 1"
    )).scalar()
    if not modulo:
        return
    conn.execute(sa.text(
        "DELETE FROM adm_permiso_opcion WHERE opcion_id IN "
        "(SELECT id FROM adm_opcion WHERE codigo = :c AND modulo_id = :m)"
    ), {"c": CODIGO, "m": modulo})
    conn.execute(sa.text(
        "DELETE FROM adm_opcion WHERE codigo = :c AND modulo_id = :m"
    ), {"c": CODIGO, "m": modulo})
    conn.execute(sa.text(
        "UPDATE adm_opcion SET orden = orden - 1 WHERE modulo_id = :m AND orden > 3"
    ), {"m": modulo})
