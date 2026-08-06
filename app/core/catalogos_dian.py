"""Catálogos DIAN pequeños que no ameritan tabla.

Son fijos, cambian solo si la DIAN publica un anexo técnico nuevo, y se
consultan siempre completos: vivir en código es más simple que en BD.
"""

# Tipos de documento de identificación (Resolución 000042 de 2020, anexo técnico).
TIPOS_DOCUMENTO = [
    {"codigo": "11", "nombre": "Registro civil"},
    {"codigo": "12", "nombre": "Tarjeta de identidad"},
    {"codigo": "13", "nombre": "Cédula de ciudadanía"},
    {"codigo": "21", "nombre": "Tarjeta de extranjería"},
    {"codigo": "22", "nombre": "Cédula de extranjería"},
    {"codigo": "31", "nombre": "NIT"},
    {"codigo": "41", "nombre": "Pasaporte"},
    {"codigo": "42", "nombre": "Documento de identificación extranjero"},
    {"codigo": "47", "nombre": "PEP (Permiso Especial de Permanencia)"},
    {"codigo": "50", "nombre": "NIT de otro país"},
    {"codigo": "91", "nombre": "NUIP"},
]

CODIGOS_DOCUMENTO = {t["codigo"] for t in TIPOS_DOCUMENTO}

# Documentos que identifican a un tercero del exterior.
DOCUMENTOS_EXTRANJEROS = {"41", "42", "50"}


def tipo_documento_sugerido(pais_codigo: str | None, tipo_persona: str | None) -> str:
    """Valor por defecto razonable cuando el tercero no lo tiene capturado.

    Colombia: NIT para jurídica, cédula para natural.
    Exterior: NIT de otro país para jurídica, documento extranjero para natural.
    """
    del_exterior = bool(pais_codigo) and pais_codigo.upper() != "CO"
    juridica = (tipo_persona or "").upper() == "JURIDICA"
    if del_exterior:
        return "50" if juridica else "42"
    return "31" if juridica else "13"
