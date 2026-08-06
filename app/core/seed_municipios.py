"""
Carga el catálogo DIVIPOLA del DANE (1.122 municipios) y hace el backfill de
`municipio_codigo` en empresa y terceros emparejando por nombre.

Fuente: dataset oficial `gdxc-w37w` de datos.gov.co, congelado en
`app/core/data/divipola.json` para no depender de la red al sembrar.

Es idempotente: se puede correr las veces que haga falta.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_municipios
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import unicodedata
from pathlib import Path

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.admin import AdmMunicipio

DATA = Path(__file__).parent / "data" / "divipola.json"


def _norm(s: str | None) -> str:
    """Nombre comparable: sin tildes, sin puntuación, en minúsculas."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s.strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c.isalnum() or c == " ").strip()


def cargar_catalogo(db) -> int:
    municipios = json.loads(DATA.read_text(encoding="utf-8"))
    existentes = {m.codigo for m in db.query(AdmMunicipio.codigo).all()}
    nuevos = 0
    for m in municipios:
        if m["codigo"] in existentes:
            continue
        db.add(AdmMunicipio(codigo=m["codigo"], nombre=m["nombre"],
                            depto_codigo=m["depto_codigo"], depto_nombre=m["depto_nombre"]))
        nuevos += 1
    db.flush()
    return nuevos


# Nombres frecuentes que no coinciden literal con DIVIPOLA.
ALIAS = {
    "bogota": "11001",
    "bogota dc": "11001",
    "bogota d c": "11001",
    "santafe de bogota": "11001",
    "cali": "76001",          # DIVIPOLA: "Santiago De Cali"
    "cartagena": "13001",     # DIVIPOLA: "Cartagena De Indias"
    "tunja": "15001",
    "san andres": "88001",
}


def backfill(db) -> dict:
    """Empareja ciudad/departamento en texto contra el catálogo.

    Es deliberadamente conservador: **prefiere no emparejar antes que emparejar
    mal**, porque un código equivocado sale en la factura electrónica.

    * Solo toca registros de Colombia (`pais` vacío o "Colombia"): sin esa
      condición, un tercero de Madrid (España) se emparejaría con Madrid,
      Cundinamarca, y hay decenas de homónimos así.
    * Exige que coincidan municipio Y departamento. Si el departamento no está
      capturado, acepta el municipio solo cuando su nombre es único en el país.
    """
    municipios = db.query(AdmMunicipio).all()
    por_depto_muni = {(_norm(m.depto_nombre), _norm(m.nombre)): m.codigo for m in municipios}
    por_muni: dict[str, list[str]] = {}
    for m in municipios:
        por_muni.setdefault(_norm(m.nombre), []).append(m.codigo)

    resultado = {}
    for tabla in ("adm_empresa", "adm_tercero"):
        tiene_pais = tabla == "adm_tercero"
        cols = "id, ciudad, departamento" + (", pais" if tiene_pais else "")
        filas = db.execute(text(
            f"SELECT {cols} FROM {tabla} "
            f"WHERE municipio_codigo IS NULL AND ciudad IS NOT NULL AND ciudad <> ''"
        )).fetchall()
        emparejadas, extranjeras = 0, 0
        for fila in filas:
            pais = _norm(getattr(fila, "pais", None)) if tiene_pais else ""
            if pais and pais != "colombia":
                extranjeras += 1
                continue
            ciudad, depto = _norm(fila.ciudad), _norm(fila.departamento)
            codigo = ALIAS.get(ciudad) or por_depto_muni.get((depto, ciudad))
            if not codigo and not depto:
                candidatos = por_muni.get(ciudad, [])
                codigo = candidatos[0] if len(candidatos) == 1 else None
            if codigo:
                db.execute(text(f"UPDATE {tabla} SET municipio_codigo = :c WHERE id = :i"),
                           {"c": codigo, "i": fila.id})
                emparejadas += 1
        resultado[tabla] = {
            "revisadas": len(filas), "emparejadas": emparejadas, "extranjeras": extranjeras,
            "sin_emparejar": len(filas) - emparejadas - extranjeras,
        }
    return resultado


def main() -> None:
    db = SessionLocal()
    try:
        nuevos = cargar_catalogo(db)
        total = db.query(AdmMunicipio).count()
        print(f"Catálogo DIVIPOLA: {nuevos} municipios nuevos · {total} en total")

        for tabla, r in backfill(db).items():
            print(f"  {tabla}: {r['emparejadas']}/{r['revisadas']} emparejados"
                  + (f" · {r['extranjeras']} del exterior (se omiten)" if r["extranjeras"] else "")
                  + (f" · {r['sin_emparejar']} sin emparejar (corregir en pantalla)" if r["sin_emparejar"] else ""))
        db.commit()
        print("Listo.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
