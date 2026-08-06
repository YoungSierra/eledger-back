"""
Carga el catálogo ISO 3166-1 (249 países) y hace el backfill en terceros de
`pais_codigo` (emparejando el texto de `pais`) y de `tipo_documento_dian`.

Fuente: `app/core/data/paises.json`, nombres en español.

Es idempotente. Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_paises
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import unicodedata
from pathlib import Path

from sqlalchemy import text

from app.core.catalogos_dian import tipo_documento_sugerido
from app.core.database import SessionLocal
from app.models.admin import AdmPais

DATA = Path(__file__).parent / "data" / "paises.json"

# Nombres frecuentes que no coinciden con el catálogo ISO en español.
ALIAS = {
    "usa": "US", "eeuu": "US", "ee uu": "US", "united states": "US",
    "estados unidos de america": "US",
    "uk": "GB", "inglaterra": "GB", "reino unido": "GB", "gran bretana": "GB",
    "holanda": "NL", "paises bajos": "NL",
    "corea del sur": "KR", "corea": "KR",
    "china": "CN", "republica popular china": "CN",
}


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s.strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c.isalnum() or c == " ").strip()


def cargar_catalogo(db) -> int:
    paises = json.loads(DATA.read_text(encoding="utf-8"))
    existentes = {p.codigo for p in db.query(AdmPais.codigo).all()}
    nuevos = 0
    for p in paises:
        if p["codigo"] in existentes:
            continue
        db.add(AdmPais(codigo=p["codigo"], nombre=p["nombre"]))
        nuevos += 1
    db.flush()
    return nuevos


def backfill_pais(db) -> dict:
    """Empareja el texto de `pais` contra el catálogo ISO.

    Los terceros sin país se asumen de Colombia: es el caso por defecto del
    sistema y así el tipo de documento sugerido queda correcto.
    """
    por_nombre = {_norm(p.nombre): p.codigo for p in db.query(AdmPais).all()}
    filas = db.execute(text(
        "SELECT id, pais FROM adm_tercero WHERE pais_codigo IS NULL"
    )).fetchall()
    emparejados, sin_pais, sin_emparejar = 0, 0, 0
    for fila in filas:
        nombre = _norm(fila.pais)
        if not nombre:
            codigo = "CO"
            sin_pais += 1
        else:
            codigo = ALIAS.get(nombre) or por_nombre.get(nombre)
        if codigo:
            db.execute(text("UPDATE adm_tercero SET pais_codigo = :c WHERE id = :i"),
                       {"c": codigo, "i": fila.id})
            if nombre:
                emparejados += 1
        else:
            sin_emparejar += 1
    return {"revisados": len(filas), "emparejados": emparejados,
            "sin_pais_asumidos_co": sin_pais, "sin_emparejar": sin_emparejar}


def backfill_tipo_documento(db) -> int:
    """Asigna el tipo de documento DIAN sugerido a quien no lo tenga."""
    filas = db.execute(text(
        "SELECT id, pais_codigo, tipo_persona FROM adm_tercero WHERE tipo_documento_dian IS NULL"
    )).fetchall()
    for fila in filas:
        db.execute(text("UPDATE adm_tercero SET tipo_documento_dian = :t WHERE id = :i"),
                   {"t": tipo_documento_sugerido(fila.pais_codigo, fila.tipo_persona), "i": fila.id})
    return len(filas)


def limpiar_municipio_extranjeros(db) -> int:
    """Un tercero del exterior no puede tener municipio DIVIPOLA."""
    return db.execute(text(
        "UPDATE adm_tercero SET municipio_codigo = NULL "
        "WHERE municipio_codigo IS NOT NULL AND pais_codigo IS NOT NULL AND pais_codigo <> 'CO'"
    )).rowcount


def main() -> None:
    db = SessionLocal()
    try:
        nuevos = cargar_catalogo(db)
        print(f"Catálogo ISO: {nuevos} países nuevos · {db.query(AdmPais).count()} en total")

        r = backfill_pais(db)
        print(f"  pais_codigo: {r['emparejados']} emparejados por nombre · "
              f"{r['sin_pais_asumidos_co']} sin país (se asumen Colombia)"
              + (f" · {r['sin_emparejar']} sin emparejar" if r["sin_emparejar"] else ""))

        print(f"  tipo_documento_dian: {backfill_tipo_documento(db)} asignados")
        limpiados = limpiar_municipio_extranjeros(db)
        if limpiados:
            print(f"  municipio DIVIPOLA limpiado en {limpiados} terceros del exterior")
        db.commit()
        print("Listo.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
