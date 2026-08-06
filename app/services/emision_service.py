"""Emisión electrónica (agnóstica de proveedor).

Arma un documento NEUTRO desde la factura, elige el adaptador según el proveedor
configurado en `FacConfigElectronica` y persiste el resultado (CUFE + estado DIAN)
en la factura. Hoy hay adaptador para Dataico; otros PTH se enchufan aquí.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core import almacenamiento
from app.core.cifrado import descifrar
from app.models.adm import AdmTercero
from app.models.admin import AdmEmpresa, AdmMoneda
from app.models.facturacion import FacFactura, FacConfigElectronica, FacResolucion
from app.schemas.auth import UsuarioActual
from app.services.emisores import dataico, factus


def _split_numero(numero: str) -> tuple[str, str]:
    """Separa prefijo (letras) y consecutivo (dígitos finales) de p.ej. 'FE1234'."""
    i = len(numero)
    while i > 0 and numero[i - 1].isdigit():
        i -= 1
    return numero[:i], numero[i:]


def _doc_neutro(db: Session, fac: FacFactura) -> dict:
    cli = db.get(AdmTercero, fac.cliente_id)
    moneda = db.get(AdmMoneda, fac.moneda_id)
    # Municipio de la empresa emisora: respaldo cuando el cliente no lo tiene capturado.
    empresa = db.query(AdmEmpresa).filter(AdmEmpresa.activo == True).first()
    prefijo, consecutivo = _split_numero(fac.numero)
    res = (
        db.query(FacResolucion)
        .filter(FacResolucion.tipo == "FACTURA_VENTA", FacResolucion.activo == True,
                FacResolucion.fecha_desde <= fac.fecha, FacResolucion.fecha_hasta >= fac.fecha)
        .first()
    )
    items = []
    for l in sorted(fac.lineas, key=lambda x: x.orden):
        items.append({
            "descripcion": l.descripcion,
            "cantidad": l.cantidad,
            "precio_unitario": l.precio_unitario,
            "descuento_pct": l.descuento_pct,
            "iva_pct": l.iva_pct,
            "iva_tipo": l.iva_tipo,
            "subtotal": l.subtotal,
            "total_iva": l.total_iva,
            "total": l.total,
            "valor_tercero": l.valor_tercero,
        })
    return {
        "numero": fac.numero,
        "prefijo": (res.prefijo if res and res.prefijo else prefijo),
        "consecutivo": consecutivo,
        "resolution_number": res.numero_resolucion if res else None,
        "fecha": fac.fecha.isoformat() if fac.fecha else None,
        "fecha_vencimiento": fac.fecha_vencimiento.isoformat() if fac.fecha_vencimiento else None,
        "moneda": moneda.codigo if moneda else "COP",
        "trm": fac.trm,
        "notas": fac.notas,
        "document_type": "invoice",
        "emisor_municipio_codigo": empresa.municipio_codigo if empresa else None,
        "cliente": {
            "identificacion": cli.nit if cli else None,
            "dv": cli.digito_verif if cli else None,
            "tipo_persona": cli.tipo_persona if cli else None,
            "razon_social": cli.razon_social if cli else None,
            "nombre1": cli.nombre1 if cli else None,
            "apellido1": cli.apellido1 if cli else None,
            "email": cli.email if cli else None,
            "telefono": cli.telefono if cli else None,
            "direccion": cli.direccion if cli else None,
            "ciudad": cli.ciudad if cli else None,
            "departamento": cli.departamento if cli else None,
            # Código DANE (DIVIPOLA): es lo que exige la facturación electrónica.
            "municipio_codigo": cli.municipio_codigo if cli else None,
            "pais_codigo": (cli.pais_codigo if cli else None) or "CO",
            "tipo_documento_dian": cli.tipo_documento_dian if cli else None,
            "regimen": cli.regimen if cli else None,
            "responsable_iva": cli.responsable_iva if cli else False,
        },
        "items": items,
        "totales": {
            "subtotal": fac.subtotal, "total_iva": fac.total_iva,
            "total_retenciones": fac.total_retenciones, "total": fac.total,
        },
    }


def _archivar_documento(fac: FacFactura, cred: dict, base_url: str, ambiente: str, numero: str) -> list[str]:
    """Descarga el XML firmado y el PDF del PTH y los guarda en nuestro almacenamiento.

    El PTH solo conserva los documentos mientras el paquete esté vigente, pero la
    DIAN obliga al emisor a guardarlos 5 años: la copia propia es un requisito
    legal, no una comodidad.

    Nunca lanza: si el archivado falla, la factura YA fue aceptada por la DIAN y
    ese hecho no se puede perder. Devuelve la lista de avisos para informarlos.
    """
    res = factus.descargar_documentos(cred, base_url, ambiente, numero)
    base_key = f"dian/facturas/{fac.id}/{numero}"
    if res.get("xml"):
        almacenamiento.subir(f"{base_key}.xml", res["xml"], "application/xml")
        fac.xml_key = f"{base_key}.xml"
    if res.get("pdf"):
        almacenamiento.subir(f"{base_key}.pdf", res["pdf"], "application/pdf")
        fac.pdf_key = f"{base_key}.pdf"
    return res.get("errores") or []


def reintentar_archivado(db: Session, factura_id: uuid.UUID) -> dict:
    """Reintenta el archivado de una factura ya aceptada cuyo XML/PDF no se guardó."""
    fac = db.query(FacFactura).filter(FacFactura.id == factura_id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if not fac.numero_dian:
        raise HTTPException(status_code=409, detail="La factura no ha sido validada ante la DIAN")
    if fac.xml_key and fac.pdf_key:
        return {"ok": True, "mensaje": "El documento ya estaba archivado.", "avisos": []}

    cfg = db.query(FacConfigElectronica).first()
    if not cfg or not cfg.activo or cfg.proveedor != "PTH_FACTUS":
        raise HTTPException(status_code=400, detail="El archivado automático hoy solo aplica a Factus.")
    cred = _cred_factus(cfg)
    avisos = _archivar_documento(fac, cred, (cfg.credenciales or {}).get("base_url") or "",
                                 cfg.ambiente, fac.numero_dian)
    db.commit()
    return {"ok": bool(fac.xml_key and fac.pdf_key), "avisos": avisos,
            "xml": bool(fac.xml_key), "pdf": bool(fac.pdf_key)}


def _cred_factus(cfg: FacConfigElectronica) -> dict:
    """Factus usa OAuth2: client_secret y password van cifrados en la BD."""
    creds = cfg.credenciales or {}
    return {
        "client_id": creds.get("client_id"),
        "client_secret": descifrar(creds.get("client_secret", "")),
        "username": creds.get("username"),
        "password": descifrar(creds.get("password", "")),
        "numbering_range_id": creds.get("numbering_range_id"),
    }


def transmitir_factura(db: Session, factura_id: uuid.UUID, actor: UsuarioActual) -> dict:
    fac = db.query(FacFactura).filter(FacFactura.id == factura_id, FacFactura.activo == True).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if fac.estado != "contabilizada":
        raise HTTPException(status_code=409, detail="Solo se transmiten facturas contabilizadas")
    if fac.dian_estado == "aceptado":
        raise HTTPException(status_code=409, detail="La factura ya fue aceptada por la DIAN")

    cfg = db.query(FacConfigElectronica).first()
    if not cfg or not cfg.activo:
        raise HTTPException(status_code=400, detail="No hay proveedor de facturación electrónica activo. Configúralo en Administración → Facturación electrónica.")

    creds = cfg.credenciales or {}
    base_url = creds.get("base_url") or ""
    doc = _doc_neutro(db, fac)

    if cfg.proveedor == "DATAICO":
        cred = {
            "account_id": creds.get("account_id"),
            "auth_token": descifrar(creds.get("auth_token", "")),
        }
        # Numeración SETP de pruebas configurada en la cuenta Dataico (solo PRUEBAS).
        doc["test_prefix"] = creds.get("test_prefix") or ""
        doc["test_resolution_number"] = creds.get("test_resolution_number") or ""
        res = dataico.emitir(cred, base_url, cfg.ambiente, doc)
    elif cfg.proveedor == "PTH_FACTUS":
        # La numeración la resuelve Factus con numbering_range_id, no con la resolución.
        cred = _cred_factus(cfg)
        res = factus.emitir(cred, base_url, cfg.ambiente, doc)
    else:
        raise HTTPException(status_code=400, detail=f"El adaptador para {cfg.proveedor} aún no está implementado. Hoy: Dataico y Factus.")

    # Mapear el estado del adaptador al valor permitido por chk_fac_dian_estado
    # (pendiente | enviada | aceptada | rechazada). 'error' de transporte/config
    # no cambia el estado (la factura sigue 'pendiente' de envío).
    MAP = {"aceptado": "aceptada", "rechazado": "rechazada", "pendiente": "enviada"}
    nuevo_estado = MAP.get(res.estado)

    if res.cufe:
        fac.cufe = res.cufe
    numero_dian = getattr(res, "numero", None)
    if numero_dian:
        fac.numero_dian = numero_dian
    if nuevo_estado:
        fac.dian_estado = nuevo_estado
        if nuevo_estado in ("aceptada", "enviada"):
            fac.fecha_dian = datetime.now(timezone.utc)
        fac.modificado_por = uuid.UUID(actor.id)
        fac.modificado_en = datetime.now(timezone.utc)

    # Archivo propio del XML/PDF. Va después de fijar el estado y nunca interrumpe:
    # la aceptación de la DIAN ya ocurrió y no se puede perder por un fallo de descarga.
    avisos: list[str] = []
    if cfg.proveedor == "PTH_FACTUS" and res.estado == "aceptado" and numero_dian:
        try:
            avisos = _archivar_documento(fac, cred, base_url, cfg.ambiente, numero_dian)
        except Exception as e:
            avisos = [f"No se pudo archivar el documento: {e.__class__.__name__}"]

    db.commit()

    return {
        "ok": res.ok,
        "dian_estado": fac.dian_estado,
        "cufe": res.cufe,
        "numero_dian": fac.numero_dian,
        "archivado": bool(fac.xml_key and fac.pdf_key),
        "mensaje": res.mensaje,
        "errores": res.errores,
        "avisos": avisos,
    }
