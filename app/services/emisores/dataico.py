"""Adaptador de emisión electrónica — Dataico.

Toma un documento NEUTRO (dict que arma `emision_service`) y lo transforma al
JSON del API de Dataico, lo transmite y normaliza la respuesta (CUFE, estado,
mensaje). Dataico construye el UBL y firma; nosotros solo mandamos el JSON.

⚠️ Los nombres exactos de campos del payload deben verificarse contra la
documentación de Dataico y ajustarse contra el ambiente de PRUEBAS. Todo el
mapeo específico de Dataico vive AQUÍ, aislado del resto del sistema, para que
ese ajuste no toque nada más. Los puntos a confirmar están marcados con `# TODO doc`.
"""
from dataclasses import dataclass, field
from decimal import Decimal

import httpx

DATAICO_BASE_PRODUCCION = "https://api.dataico.com/direct/dataico_api/v2"
TIMEOUT = 30.0


@dataclass
class ResultadoEmision:
    ok: bool
    estado: str            # "aceptado" | "rechazado" | "pendiente" | "error"
    cufe: str | None = None
    mensaje: str = ""
    raw: dict | None = None
    errores: list[str] = field(default_factory=list)


def _num(v) -> float:
    return float(Decimal(str(v or "0")))


def _fecha(iso: str | None) -> str | None:
    """ISO 'YYYY-MM-DD' -> 'DD/MM/YYYY' (formato que espera Dataico)."""
    if not iso:
        return None
    p = iso.split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else iso


def _party_type(tp: str | None) -> str:
    return "PERSONA_JURIDICA" if (tp or "").upper() == "JURIDICA" else "PERSONA_NATURAL"


def _party_id_type(tp: str | None) -> str:
    # Sin catálogo por tercero: jurídica -> NIT, natural -> CC (default razonable).
    return "NIT" if (tp or "").upper() == "JURIDICA" else "CC"


def _map_item(it: dict) -> dict:
    qty = _num(it.get("cantidad")) or 1
    subtotal = _num(it.get("subtotal"))
    total_iva = _num(it.get("total_iva"))
    iva_pct = _num(it.get("iva_pct"))
    precio = _num(it.get("precio_unitario"))
    item = {
        "description": it.get("descripcion") or "",
        "quantity": qty,
        "price": precio,
        "discount-rate": _num(it.get("descuento_pct")),
        "measuring-unit": it.get("measuring_unit") or "94",  # 94 = "unidad" (catálogo DIAN); ajustable
        "taxes": [],
    }
    if iva_pct > 0:
        item["taxes"].append({
            "tax-category": "IVA",
            "tax-rate": iva_pct,
            "tax-amount": total_iva,
            "tax-base": subtotal,
            "base-amount": subtotal,
        })
    return item


def construir_payload(doc: dict, ambiente: str, account_id: str) -> dict:
    """Documento neutro -> JSON del API v2 de Dataico (POST /invoices)."""
    cli = doc.get("cliente", {})
    juridica = (cli.get("tipo_persona") or "").upper() == "JURIDICA"
    es_pruebas = (ambiente or "").upper() == "PRUEBAS"
    invoice = {
        "issue_date": _fecha(doc.get("fecha")),
        "invoice_type_code": doc.get("invoice_type_code", "FACTURA_VENTA"),
        "operation": "ESTANDAR",
        "currency": doc.get("moneda") or "COP",
        "dataico_account_id": account_id,
        "env": "PRUEBAS" if es_pruebas else "PRODUCCION",
        "notes": [n for n in [doc.get("notas")] if n],
        "customer": {
            "party_type": _party_type(cli.get("tipo_persona")),
            "party_identification": cli.get("identificacion"),
            "party_identification_type": _party_id_type(cli.get("tipo_persona")),
            "company_name": cli.get("razon_social") if juridica else None,
            "first_name": None if juridica else cli.get("nombre1"),
            "family_name": None if juridica else cli.get("apellido1"),
            "email": cli.get("email"),
            "phone": cli.get("telefono"),
            "address_line": cli.get("direccion"),
            "city": cli.get("ciudad"),
            "department": cli.get("departamento"),
            "country_code": "CO",
            # tax_level_code / regimen: catálogo DIAN de responsabilidades; se afina con la respuesta de Dataico.
            "regimen": cli.get("regimen"),
        },
        "items": [_map_item(it) for it in doc.get("items", [])],
    }
    # Numeración/resolución DIAN. Dataico exige una numeración REGISTRADA en la cuenta.
    #  - PRUEBAS: se usa la numeración SETP de habilitación configurada en la cuenta
    #    (test_prefix / test_resolution_number). El número lo asigna Dataico (flexible).
    #  - PRODUCCIÓN: se usa la resolución real del cliente + el consecutivo del sistema.
    if es_pruebas:
        if doc.get("test_resolution_number") or doc.get("test_prefix"):
            invoice["numbering"] = {
                "resolution_number": doc.get("test_resolution_number") or None,
                "prefix": doc.get("test_prefix") or "",
                "flexible": True,
            }
    elif doc.get("resolution_number") or doc.get("prefijo"):
        invoice["number"] = doc.get("consecutivo") or doc.get("numero")
        invoice["numbering"] = {
            "resolution_number": doc.get("resolution_number"),
            "prefix": doc.get("prefijo") or "",
            "flexible": True,
        }
    # Moneda extranjera -> TRM.
    if invoice["currency"] != "COP" and doc.get("trm"):
        invoice["currency_exchange_rate"] = _num(doc["trm"])
        invoice["currency_exchange_rate_date"] = _fecha(doc.get("fecha"))
    return {
        "actions": {"send_dian": True, "send_email": False},
        "invoice": invoice,
    }


def _flatten_errores(v, prefijo="") -> list[str]:
    """Aplana el {errors:{campo:[msgs], sub:{...}}} de Dataico a strings legibles."""
    out = []
    if isinstance(v, dict):
        for k, val in v.items():
            out += _flatten_errores(val, f"{prefijo}{k}: " if not prefijo else f"{prefijo}{k}: ")
    elif isinstance(v, list):
        for x in v:
            if isinstance(x, (dict, list)):
                out += _flatten_errores(x, prefijo)
            else:
                out.append(f"{prefijo}{x}".strip())
    elif v is not None:
        out.append(f"{prefijo}{v}".strip())
    return out


def _parse_respuesta(status_code: int, body: dict) -> ResultadoEmision:
    """Normaliza la respuesta del API v2 de Dataico."""
    errores = _flatten_errores(body.get("errors")) if body.get("errors") else []
    if status_code >= 400 or errores:
        msg = body.get("message") or "Factura rechazada por validación."
        return ResultadoEmision(ok=False, estado="rechazado" if status_code < 500 or errores else "error",
                                mensaje=msg, raw=body, errores=errores)

    cufe = body.get("cufe")
    uuid_ = body.get("uuid")
    est = (body.get("dian_status") or "").upper()
    extra = " · ".join([x for x in [body.get("pdf_url")] if x])
    if "ACEPTAD" in est:
        return ResultadoEmision(ok=True, estado="aceptado", cufe=cufe,
                                mensaje=f"Aceptada por la DIAN. {extra}".strip(), raw=body)
    if "RECHAZAD" in est:
        return ResultadoEmision(ok=False, estado="rechazado", cufe=cufe,
                                mensaje="Rechazada por la DIAN.", raw=body,
                                errores=_flatten_errores(body.get("dian_errors")) if body.get("dian_errors") else [])
    # 201 sin veredicto final (en proceso)
    return ResultadoEmision(ok=True, estado="pendiente", cufe=cufe,
                            mensaje=body.get("dian_status") or "Transmitida; DIAN en proceso.", raw=body)


def emitir(cred: dict, base_url: str, ambiente: str, doc: dict) -> ResultadoEmision:
    account_id = cred.get("account_id") or ""
    token = cred.get("auth_token") or ""
    if not account_id or not token:
        return ResultadoEmision(ok=False, estado="error", mensaje="Faltan Account ID o Auth-Token de Dataico.")
    url = f"{(base_url or DATAICO_BASE_PRODUCCION).rstrip('/')}/invoices"
    payload = construir_payload(doc, ambiente, account_id)
    try:
        r = httpx.post(
            url,
            headers={"Dataico_account_id": account_id, "Auth-Token": token, "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT,
        )
    except httpx.RequestError as e:
        return ResultadoEmision(ok=False, estado="error", mensaje=f"No se pudo contactar a Dataico: {e.__class__.__name__}")
    try:
        body = r.json()
    except Exception:
        body = {"raw_text": r.text}
    return _parse_respuesta(r.status_code, body if isinstance(body, dict) else {"data": body})
