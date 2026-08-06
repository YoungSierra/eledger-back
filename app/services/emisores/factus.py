"""Adaptador de emisión electrónica — Factus (Halltec).

Mismo contrato que `dataico.py`: recibe el documento NEUTRO que arma
`emision_service`, lo transforma al JSON de Factus API v2, lo transmite y
normaliza la respuesta en un `ResultadoEmision`.

Diferencias frente a Dataico que condicionan este adaptador:

* **Autenticación OAuth2** (`POST /oauth/token`, grant_type=password) en vez de
  headers fijos. El token dura 1 hora, así que se cachea en memoria por
  client_id y se renueva solo cuando faltan menos de 60 s.
* **La numeración vive en Factus**, no en el payload: se manda
  `numbering_range_id` (el id del rango ya asociado en la cuenta) y Factus
  asigna el consecutivo. Nuestro `fac_factura.numero` viaja como
  `reference_code` para poder cruzar los dos números.
* **Todo es catálogo DIAN por código** (municipio, tipo de documento de
  identidad, organización jurídica, tributo, unidad de medida).

* **Clientes del exterior**: no llevan `municipality_code` (DIVIPOLA es solo de
  Colombia) ni dígito de verificación, su `country_code` es el ISO real, y con
  documento extranjero la razón social viaja en `names` porque Factus ignora
  `company`. Ver `_es_exterior()`.
"""
import base64
import threading
import time
from dataclasses import dataclass, field
from decimal import Decimal

import httpx

from app.core.catalogos_dian import DOCUMENTOS_EXTRANJEROS, tipo_documento_sugerido

FACTUS_BASE_PRODUCCION = "https://api.factus.com.co"
FACTUS_BASE_SANDBOX = "https://api-sandbox.factus.com.co"
TIMEOUT = 60.0

# Catálogos DIAN — solo lo que usamos.
DOC_FACTURA_VENTA = "01"
OPERACION_ESTANDAR = "10"
TRIBUTO_IVA = "01"
TRIBUTO_NO_APLICA = "ZZ"
UNIDAD_DEFECTO = "94"          # 94 = "unidad"
STANDARD_CODE_DEFECTO = "999"  # 999 = estándar propio del vendedor
MUNICIPIO_DEFECTO = "11001"    # Bogotá D.C. — último respaldo, ver _municipio()


@dataclass
class ResultadoEmision:
    ok: bool
    estado: str            # "aceptado" | "rechazado" | "pendiente" | "error"
    cufe: str | None = None
    mensaje: str = ""
    raw: dict | None = None
    errores: list[str] = field(default_factory=list)
    numero: str | None = None   # consecutivo fiscal que asignó Factus (p.ej. SETP990014207)


# --------------------------------------------------------------------------- #
# Token OAuth2 (cache en memoria; el token dura 1 h)
# --------------------------------------------------------------------------- #
_tokens: dict[str, tuple[str, float]] = {}
_tokens_lock = threading.Lock()


def _base(base_url: str | None, ambiente: str) -> str:
    if base_url:
        return base_url.rstrip("/")
    return FACTUS_BASE_SANDBOX if (ambiente or "").upper() == "PRUEBAS" else FACTUS_BASE_PRODUCCION


def obtener_token(cred: dict, base: str) -> tuple[str | None, str]:
    """Devuelve (access_token, mensaje_error). Cachea por client_id + base."""
    cid = cred.get("client_id") or ""
    clave = f"{base}|{cid}|{cred.get('username') or ''}"
    ahora = time.time()
    with _tokens_lock:
        cacheado = _tokens.get(clave)
        if cacheado and cacheado[1] - ahora > 60:
            return cacheado[0], ""
    try:
        r = httpx.post(
            f"{base}/oauth/token",
            data={
                "grant_type": "password",
                "client_id": cid,
                "client_secret": cred.get("client_secret") or "",
                "username": cred.get("username") or "",
                "password": cred.get("password") or "",
            },
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
        )
    except httpx.RequestError as e:
        return None, f"No se pudo contactar a Factus: {e.__class__.__name__}"
    if r.status_code != 200:
        try:
            detalle = r.json().get("message") or r.text[:200]
        except Exception:
            detalle = r.text[:200]
        return None, f"Autenticación rechazada por Factus ({r.status_code}): {detalle}"
    body = r.json()
    token = body.get("access_token")
    if not token:
        return None, "Factus no devolvió access_token."
    with _tokens_lock:
        _tokens[clave] = (token, ahora + float(body.get("expires_in") or 3600))
    return token, ""


# --------------------------------------------------------------------------- #
# Mapeo del documento neutro -> payload de Factus
# --------------------------------------------------------------------------- #
def _num(v) -> Decimal:
    return Decimal(str(v or "0"))


def _s(v) -> str:
    """Decimal -> string con 2 decimales (Factus recibe los montos como texto)."""
    return f"{_num(v):.2f}"


def _tipo_doc_identidad(cli: dict) -> str:
    """Catálogo DIAN de tipo de documento. Lo manda el tercero; si no lo tiene
    capturado, se sugiere uno según país y tipo de persona."""
    cod = (cli.get("tipo_documento_dian") or "").strip()
    return cod or tipo_documento_sugerido(cli.get("pais_codigo"), cli.get("tipo_persona"))


def _organizacion_juridica(cli: dict) -> str:
    """1 = Persona Jurídica · 2 = Persona Natural."""
    return "1" if (cli.get("tipo_persona") or "").upper() == "JURIDICA" else "2"


def _es_exterior(cli: dict) -> bool:
    return (cli.get("pais_codigo") or "CO").upper() != "CO"


def _municipio(cli: dict, doc: dict) -> str:
    """Código DANE de 5 dígitos del municipio del cliente.

    Factus NO expone catálogo de municipios en v2, así que el código tiene que
    venir del maestro. Orden: el del tercero → el de la empresa emisora → Bogotá.
    Los dos primeros salen del catálogo DIVIPOLA (`adm_municipio`).
    """
    cod = (cli.get("municipio_codigo") or "").strip()
    if cod:
        return cod
    return (doc.get("emisor_municipio_codigo") or "").strip() or MUNICIPIO_DEFECTO


def _map_item(it: dict) -> dict:
    """Una línea neutra -> un ítem de Factus.

    Factus liquida los impuestos por su cuenta: se le manda la tarifa, no el
    valor. `price` es el precio unitario ANTES de IVA y el descuento va como
    porcentaje.
    """
    iva_pct = _num(it.get("iva_pct"))
    iva_tipo = (it.get("iva_tipo") or "").upper()
    # Excluido y exento NO son lo mismo y Factus los distingue (confirmado por
    # ellos el 2026-08-01): excluido viaja con `is_excluded: 1` y sin impuestos;
    # exento viaja como gravado con tarifa 0%. Antes ambos caían en "excluido",
    # que declara mal ante la DIAN un servicio exento.
    excluido = iva_tipo == "EXCLUIDO" or (iva_pct <= 0 and iva_tipo not in ("EXENTO", "GRAVADO_19", "GRAVADO_5"))
    item = {
        "code_reference": (it.get("codigo") or "GEN")[:50],
        "name": (it.get("descripcion") or "Servicio")[:300],
        "quantity": _s(it.get("cantidad") or 1),
        "discount_rate": _s(it.get("descuento_pct")),
        "price": _s(it.get("precio_unitario")),
        "unit_measure_code": str(it.get("unit_measure_code") or UNIDAD_DEFECTO),
        "standard_code": str(it.get("standard_code") or STANDARD_CODE_DEFECTO),
        "is_excluded": 1 if excluido else 0,
        "tribute_code": TRIBUTO_IVA,
        "taxes": [],
    }
    # `taxes` no puede ir vacío salvo en excluido: la API lo exige.
    if not excluido:
        item["taxes"].append({"code": TRIBUTO_IVA, "rate": _s(iva_pct)})
    return item


def construir_payload(doc: dict, cred: dict) -> dict:
    """Documento neutro -> JSON de `POST /v2/bills/validate`."""
    cli = doc.get("cliente", {})
    juridica = (cli.get("tipo_persona") or "").upper() == "JURIDICA"
    total = _num((doc.get("totales") or {}).get("total"))
    # Contado si no hay fecha de vencimiento distinta a la de emisión.
    a_credito = bool(doc.get("fecha_vencimiento")) and doc.get("fecha_vencimiento") != doc.get("fecha")

    tipo_doc = _tipo_doc_identidad(cli)
    exterior = _es_exterior(cli)
    # Verificado contra la API: con documento extranjero (50 "NIT otro país")
    # Factus reclasifica al cliente como persona natural e IGNORA `company` —
    # la razón social solo aparece si viaja en `names`.
    razon = (cli.get("razon_social") or "")[:200]
    usa_company = juridica and tipo_doc not in DOCUMENTOS_EXTRANJEROS

    # Factus valida `names`/`surnames` como string aunque el cliente sea jurídico:
    # se mandan siempre, vacíos cuando aplica `company`.
    customer = {
        "identification": (cli.get("identificacion") or "").strip(),
        "identification_document_code": tipo_doc,
        "legal_organization_code": _organizacion_juridica(cli),
        "tribute_code": TRIBUTO_IVA if cli.get("responsable_iva") else TRIBUTO_NO_APLICA,
        "company": razon if usa_company else "",
        "trade_name": razon if usa_company else "",
        "names": "" if usa_company else (
            razon[:100] if juridica else (cli.get("nombre1") or razon)[:100]
        ),
        "surnames": "" if juridica else (cli.get("apellido1") or "")[:100],
        "email": cli.get("email") or "",
        "phone": (cli.get("telefono") or "")[:20],
        "address": (cli.get("direccion") or "")[:200],
        "country_code": (cli.get("pais_codigo") or "CO").upper(),
    }
    # El municipio DIVIPOLA solo existe dentro de Colombia: mandarlo para un
    # cliente del exterior reportaría a la DIAN una ciudad colombiana falsa.
    if not exterior:
        customer["municipality_code"] = _municipio(cli, doc)
    # El dígito de verificación es colombiano; un NIT extranjero no lo tiene.
    if cli.get("dv") and not exterior:
        customer["dv"] = str(cli["dv"])

    payload = {
        "numbering_range_id": int(cred.get("numbering_range_id") or 0),
        "reference_code": doc.get("numero") or "",
        "document": DOC_FACTURA_VENTA,
        "operation_type": OPERACION_ESTANDAR,
        "send_email": False,
        "observation": (doc.get("notas") or "")[:500],
        "payment_form": "2" if a_credito else "1",
        "payment_method_code": "10",     # 10 = efectivo (catálogo DIAN de medios de pago)
        "payment_due_date": doc.get("fecha_vencimiento") or None,
        "customer": customer,
        "items": [_map_item(it) for it in doc.get("items", [])],
    }
    payload["payment_details"] = [{
        "payment_form": payload["payment_form"],
        "payment_method_code": payload["payment_method_code"],
        "reference_code": doc.get("numero") or "",
        "amount": _s(total),
        # Obligatoria aun de contado; sin vencimiento se usa la fecha de emisión.
        "due_date": doc.get("fecha_vencimiento") or doc.get("fecha"),
    }]
    if (doc.get("moneda") or "COP") != "COP" and doc.get("trm"):
        payload["currency_code"] = doc["moneda"]
        payload["exchange_rate"] = _s(doc["trm"])
    return payload


# --------------------------------------------------------------------------- #
# Respuesta
# --------------------------------------------------------------------------- #
def _flatten_errores(v, prefijo="") -> list[str]:
    """Aplana {errors:{campo:[msgs]}} (o una lista suelta) a strings legibles."""
    out = []
    if isinstance(v, dict):
        for k, val in v.items():
            out += _flatten_errores(val, f"{prefijo}{k}: ")
    elif isinstance(v, list):
        for x in v:
            out += _flatten_errores(x, prefijo) if isinstance(x, (dict, list)) else [f"{prefijo}{x}".strip()]
    elif v is not None:
        out.append(f"{prefijo}{v}".strip())
    return out


def _parse_respuesta(status_code: int, body: dict) -> ResultadoEmision:
    data = body.get("data") or {}
    errores = _flatten_errores(body.get("errors")) if body.get("errors") else []
    if not errores and data.get("errors"):
        errores = _flatten_errores(data["errors"])

    if status_code >= 400 or (status_code >= 400 and errores):
        msg = body.get("message") or "Factura rechazada por Factus."
        # 422/400 = validación (rechazo); 5xx = problema del proveedor.
        return ResultadoEmision(ok=False, estado="rechazado" if status_code < 500 else "error",
                                mensaje=msg, raw=body, errores=errores)

    cufe = data.get("cufe")
    numero = data.get("number")
    links = data.get("links") or {}
    if data.get("is_validated") and cufe:
        extra = links.get("public_url") or ""
        return ResultadoEmision(
            ok=True, estado="aceptado", cufe=cufe, numero=numero,
            mensaje=f"Validada por la DIAN como {numero}. {extra}".strip(), raw=body,
        )
    if errores:
        return ResultadoEmision(ok=False, estado="rechazado", mensaje=body.get("message") or "Rechazada.",
                                raw=body, errores=errores, numero=numero)
    return ResultadoEmision(ok=True, estado="pendiente", cufe=cufe, numero=numero,
                            mensaje=body.get("message") or "Transmitida; DIAN en proceso.", raw=body)


# --------------------------------------------------------------------------- #
# Emisión
# --------------------------------------------------------------------------- #
def emitir(cred: dict, base_url: str, ambiente: str, doc: dict) -> ResultadoEmision:
    faltan = [c for c in ("client_id", "client_secret", "username", "password") if not cred.get(c)]
    if faltan:
        return ResultadoEmision(ok=False, estado="error",
                                mensaje=f"Faltan credenciales de Factus: {', '.join(faltan)}.")
    if not cred.get("numbering_range_id"):
        return ResultadoEmision(ok=False, estado="error",
                                mensaje="Falta el ID del rango de numeración (numbering_range_id) de Factus.")

    base = _base(base_url, ambiente)
    token, err = obtener_token(cred, base)
    if not token:
        return ResultadoEmision(ok=False, estado="error", mensaje=err)

    payload = construir_payload(doc, cred)
    try:
        r = httpx.post(
            f"{base}/v2/bills/validate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                     "Accept": "application/json"},
            json=payload,
            timeout=TIMEOUT,
        )
    except httpx.RequestError as e:
        return ResultadoEmision(ok=False, estado="error",
                                mensaje=f"No se pudo contactar a Factus: {e.__class__.__name__}")
    try:
        body = r.json()
    except Exception:
        body = {"raw_text": r.text}
    return _parse_respuesta(r.status_code, body if isinstance(body, dict) else {"data": body})


def descargar_documentos(cred: dict, base_url: str, ambiente: str, numero: str) -> dict:
    """Descarga el XML firmado y el PDF de un documento ya validado.

    Factus solo conserva los documentos mientras el paquete esté vigente, pero
    la DIAN exige al emisor conservarlos 5 años: por eso se archivan en nuestro
    propio almacenamiento apenas se emiten.

    Devuelve `{"xml": bytes|None, "pdf": bytes|None, "file_name": str, "errores": [str]}`.
    Nunca lanza: si algo falla, el error va en `errores` y el binario queda en None.
    """
    salida: dict = {"xml": None, "pdf": None, "file_name": "", "errores": []}
    if not numero:
        salida["errores"].append("Sin número de documento; no hay qué descargar.")
        return salida

    base = _base(base_url, ambiente)
    token, err = obtener_token(cred, base)
    if not token:
        salida["errores"].append(err)
        return salida
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    for clave, ruta, campo in (
        ("xml", "download-xml", "xml_base_64_encoded"),
        ("pdf", "download-pdf", "pdf_base_64_encoded"),
    ):
        try:
            r = httpx.get(f"{base}/v2/bills/{numero}/{ruta}", headers=headers, timeout=TIMEOUT)
            if r.status_code != 200:
                salida["errores"].append(f"{clave.upper()}: Factus respondió {r.status_code}.")
                continue
            data = r.json().get("data") or {}
            b64 = data.get(campo)
            if not b64:
                salida["errores"].append(f"{clave.upper()}: la respuesta no trae {campo}.")
                continue
            salida[clave] = base64.b64decode(b64)
            salida["file_name"] = salida["file_name"] or (data.get("file_name") or "")
        except Exception as e:  # red, base64 corrupto, JSON inesperado
            salida["errores"].append(f"{clave.upper()}: {e.__class__.__name__}")
    return salida


def probar_conexion(cred: dict, base_url: str, ambiente: str) -> tuple[bool, str]:
    """Autentica y lista los rangos de numeración. Para el botón 'Probar conexión'."""
    base = _base(base_url, ambiente)
    token, err = obtener_token(cred, base)
    if not token:
        return False, err
    try:
        r = httpx.get(f"{base}/v2/numbering-ranges",
                      headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                      timeout=TIMEOUT)
    except httpx.RequestError as e:
        return False, f"No se pudo contactar a Factus: {e.__class__.__name__}"
    if r.status_code != 200:
        return False, f"Factus respondió {r.status_code}: {r.text[:200]}"
    rangos = ((r.json().get("data") or {}).get("data")) or []
    facturas = [x for x in rangos if "Factura" in (x.get("document") or "")]
    if not facturas:
        return True, "Conexión OK, pero la cuenta no tiene rangos de numeración de factura de venta."
    detalle = " · ".join(f"{x.get('prefix')} (id {x.get('id')})" for x in facturas[:5])
    return True, f"Conexión OK. Rangos de factura disponibles: {detalle}"
