"""Sincronización del municipio DIVIPOLA.

`municipio_codigo` es la fuente de verdad, pero `ciudad` y `departamento` se
conservan como texto porque los leen impresiones, reportes, Excel y el portal.
Este helper mantiene los tres campos coherentes al guardar.
"""
from sqlalchemy.orm import Session

from app.models.admin import AdmMunicipio, AdmPais


def sincronizar(db: Session, obj, codigo: str | None) -> None:
    """Fija `municipio_codigo` en `obj` y deriva `ciudad`/`departamento`.

    `codigo` en None deja el objeto como está (el llamador no envió el campo);
    en "" limpia la referencia pero conserva el texto que hubiera capturado.
    """
    if codigo is None:
        return
    codigo = codigo.strip()
    if not codigo:
        obj.municipio_codigo = None
        return
    muni = db.get(AdmMunicipio, codigo)
    if not muni:
        raise ValueError(f"El municipio {codigo} no existe en el catálogo DIVIPOLA")
    obj.municipio_codigo = muni.codigo
    obj.ciudad = muni.nombre
    obj.departamento = muni.depto_nombre


def sincronizar_pais(db: Session, obj, codigo: str | None) -> None:
    """Fija `pais_codigo` y deriva `pais` en texto.

    Si el país no es Colombia, limpia `municipio_codigo`: el catálogo DIVIPOLA
    solo aplica dentro del país, y dejar un municipio colombiano en un tercero
    del exterior haría que la factura electrónica reporte una ciudad falsa.
    """
    if codigo is None:
        return
    codigo = (codigo or "").strip().upper()
    if not codigo:
        obj.pais_codigo = None
        return
    pais = db.get(AdmPais, codigo)
    if not pais:
        raise ValueError(f"El país {codigo} no existe en el catálogo ISO")
    obj.pais_codigo = pais.codigo
    obj.pais = pais.nombre
    if pais.codigo != "CO":
        obj.municipio_codigo = None
