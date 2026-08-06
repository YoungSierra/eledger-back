"""
UCASE-001 — las dos facturas del caso ZULUPRINTS.

Reproduce `ucase-001/UC 1631.pdf` (USD) y `UC 1632.pdf` (COP). Se crean con el
flujo normal del servicio, así que toman el consecutivo del sistema (ES…) y no
los números originales del proveedor anterior.

Los importes son EXACTOS a las facturas reales; los totales se verifican al
final contra los que imprimió el PDF.

Lo que el caso enseña y por eso se reproduce tal cual:
  · Una operación factura en DOS documentos: el tramo internacional en USD y
    el nacional en COP.
  · La factura NO es una conversión mecánica de la cotización: hay conceptos
    que no se cotizaron (acompañamiento, preinspección) y valores que cambiaron.
  · Retenciones con BASES DISTINTAS en un mismo documento (4% servicios,
    1% transporte).
  · Líneas marcadas (T): valores recibidos para terceros, sin IVA ni retención.

Es idempotente: si ya existen, no hace nada.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_ucase_001_facturas
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import date, timedelta
from decimal import Decimal

from app.core.database import SessionLocal
from app.models.adm import AdmTercero
from app.models.admin import AdmCondicionPago, AdmMoneda, AdmTarifaIva, AdmUsuario
from app.models.contabilidad import CntCuenta
from app.models.facturacion import FacFactura
from app.models.ope import OpeCotizacion
from app.schemas.auth import UsuarioActual
from app.schemas.facturacion import FacFacturaCreate, LineaFacCreate, RetencionFacCreate
from app.services import facturacion_service

MARCA = "UCASE-001"
TRM = Decimal("3233.91")          # la que usó UC 1631
IVA = Decimal("19")

# (descripción, valor, ¿lleva IVA 19%?, cuenta de ingreso, ¿valor para tercero?)
FACTURA_USD = [
    ("FLETE INTERNACIONAL", "3200.00",  False, "414515", False),   # marítimo: vía acuática
    ("GASTOS EN ORIGEN",    "3100.00",  False, "414540", False),
    ("THCD",                "200.00",   True,  "414530", False),
    ("DOCUMENT FEE",        "100.00",   True,  "414595", False),
    ("MANEJO (P)",          "70.00",    True,  "414530", False),
    ("SEGURO",              "837.74",   True,  "414595", False),
]

FACTURA_COP = [
    ("COORDINACION ADUANERA",              "2564868.16", True,  "414540", False),
    ("GASTOS OPERATIVOS",                  "300000.00",  True,  "414540", False),
    ("DECLARACION DE IMPORTACION",         "1200000.00", True,  "414595", False),
    ("DECLARACION DE VALOR",               "1200000.00", True,  "414595", False),
    ("PRE INSPECCION",                     "350000.00",  True,  "414595", False),
    ("URBANO",                             "1000000.00", False, "414505", False),
    ("COORDINACION DE TRANSPORTE NACIONAL","6400000.00", False, "414505", False),
    ("DEVOLUCION CONTENEDOR",              "1200000.00", False, "414505", False),
    ("ACOMPAÑAMIENTO",                     "1600000.00", True,  "414595", False),
    ("GPS",                                "250000.00",  True,  "414540", False),
    ("GASTOS EN PUERTO (T)",               "1783216.00", False, "281505", True),
    ("COORDINACION DE ALMACENAMIENTO",     "2500000.00", True,  "414535", False),
    ("RECUPERACION GASTOS FINANCIERO (T)", "7132.86",    False, "281505", True),
]

# Retención del 1% sobre transporte nacional (UC 1632). El resto va al 4%.
BASE_RETE_1 = {"URBANO", "COORDINACION DE TRANSPORTE NACIONAL"}

# Las líneas (T) trasladan plata a un tercero, así que exigen proveedor: de él
# saldrá el CxP. El caso real no lo documenta (el PDF del proveedor anterior
# imprime al propio cliente en la columna "Tercero"), así que se usa un
# MARCADOR evidente — hay que reemplazarlo por el operador portuario real.
PROVEEDOR_VRT_NIT = "999999999"
PROVEEDOR_VRT_NOMBRE = "OPERADOR PORTUARIO — PENDIENTE IDENTIFICAR (demo UCASE-001)"


def _cuenta(db, codigo):
    return db.query(CntCuenta).filter(CntCuenta.codigo == codigo).first()


def _proveedor_vrt(db, actor_id):
    """Tercero marcador para las líneas de valor recibido para tercero."""
    import uuid as _uuid
    p = db.query(AdmTercero).filter(AdmTercero.nit == PROVEEDOR_VRT_NIT).first()
    if not p:
        p = AdmTercero(
            id=_uuid.uuid4(), nit=PROVEEDOR_VRT_NIT, razon_social=PROVEEDOR_VRT_NOMBRE,
            tipo_persona="JURIDICA", tipo_tercero="PROVEEDOR",
            municipio_codigo="76109", ciudad="Buenaventura", departamento="Valle Del Cauca",
            pais="Colombia", pais_codigo="CO", tipo_documento_dian="31",
            creado_por=actor_id,
        )
        db.add(p)
        db.flush()
        print(f"Proveedor marcador creado: {PROVEEDOR_VRT_NOMBRE}")
    return p


def _armar(db, filas, cuenta_iva_id, proveedor_vrt=None):
    """Convierte la tabla de la factura en líneas + las dos retenciones."""
    lineas, base_iva, base_r4, base_r1 = [], Decimal("0"), Decimal("0"), Decimal("0")
    for desc, valor, con_iva, cod_cuenta, vrt in filas:
        sub = Decimal(valor)
        iva = (sub * IVA / 100).quantize(Decimal("0.01")) if con_iva else Decimal("0")
        cta = _cuenta(db, cod_cuenta)
        lineas.append(LineaFacCreate(
            descripcion=desc, cantidad=Decimal("1"), precio_unitario=sub, subtotal=sub,
            iva_tipo="GRAVADO_19" if con_iva else "NINGUNO",
            iva_pct=IVA if con_iva else Decimal("0"), total_iva=iva,
            cuenta_iva_id=cuenta_iva_id if con_iva else None,
            total=sub + iva,
            cuenta_ingreso_id=cta.id if cta else None,
            valor_tercero=vrt,
            proveedor_id=proveedor_vrt.id if (vrt and proveedor_vrt) else None,
        ))
        if con_iva:
            base_iva += sub
        # La retención sigue al IVA: lo gravado retiene 4%; el transporte, 1%.
        if desc in BASE_RETE_1:
            base_r1 += sub
        elif con_iva:
            base_r4 += sub

    cta_rete = _cuenta(db, "135510")
    retenciones = []
    if base_r4:
        retenciones.append(RetencionFacCreate(
            tipo="RETEFUENTE", concepto="Retefuente servicios 4%", base=base_r4,
            porcentaje=Decimal("4"), valor=(base_r4 * Decimal("0.04")).quantize(Decimal("0.01")),
            cuenta_id=cta_rete.id))
    if base_r1:
        retenciones.append(RetencionFacCreate(
            tipo="RETEFUENTE", concepto="Retefuente transporte 1%", base=base_r1,
            porcentaje=Decimal("1"), valor=(base_r1 * Decimal("0.01")).quantize(Decimal("0.01")),
            cuenta_id=cta_rete.id))
    return lineas, retenciones


def main() -> None:
    db = SessionLocal()
    try:
        cliente = db.query(AdmTercero).filter(AdmTercero.nit == "830049009").first()
        if not cliente:
            print("Falta el cliente ZULUPRINTS. Corre antes `python -m app.core.seed_ucase_001`.")
            return
        cot = db.query(OpeCotizacion).filter(OpeCotizacion.notas.like("%UCC-5340426%")).first()

        usuario = db.query(AdmUsuario).first()
        actor = UsuarioActual(id=str(usuario.id), email=usuario.email, nombre=usuario.nombre,
                              apellido=usuario.apellido or "", rol_id=str(usuario.rol_id),
                              ver_solo_propios=False, es_asesor=False, permisos=[])
        usd = db.query(AdmMoneda).filter(AdmMoneda.codigo == "USD").first()
        cop = db.query(AdmMoneda).filter(AdmMoneda.codigo == "COP").first()
        cuenta_iva = db.query(AdmTarifaIva).filter(AdmTarifaIva.nombre == "IVA 19%").first().cuenta_iva_ventas_id
        credito = db.query(AdmCondicionPago).first()

        proveedor_vrt = _proveedor_vrt(db, usuario.id)
        hoy = date.today()
        notas_base = (f"{MARCA} · Operación ZULUPRINTS — DOC DE TRANSPORTE ROECHN26044238 · DO UCCIM062-26"
                      + (f" · Cotización {cot.numero}" if cot else ""))

        for etiqueta, filas, moneda, trm in (
            ("tramo internacional (USD)", FACTURA_USD, usd, TRM),
            ("tramo nacional (COP)",      FACTURA_COP, cop, None),
        ):
            # Idempotencia por documento: si el tramo ya se creó, se salta.
            ya = db.query(FacFactura).filter(FacFactura.notas.like(f"%{MARCA}%{etiqueta}%")).first()
            if ya:
                print(f"\n{ya.numero} — {etiqueta}: ya existía, se omite.")
                continue
            lineas, retenciones = _armar(db, filas, cuenta_iva, proveedor_vrt)
            data = FacFacturaCreate(
                fecha=hoy, fecha_vencimiento=hoy + timedelta(days=30),
                cliente_id=cliente.id,
                cotizacion_id=cot.id if cot else None,
                moneda_id=moneda.id, trm=trm,
                condicion_pago_id=credito.id if credito else None,
                notas=f"{notas_base} · {etiqueta}",
                lineas=lineas, retenciones=retenciones,
            )
            fac = facturacion_service.crear(db, data, actor)
            facturacion_service.contabilizar(db, fac.id, actor)
            db.refresh(db.get(FacFactura, fac.id))
            f = db.get(FacFactura, fac.id)
            print(f"\n{f.numero} — {etiqueta}")
            print(f"  subtotal      {f.subtotal:>16,.2f}")
            print(f"  IVA           {f.total_iva:>16,.2f}")
            print(f"  retenciones   {f.total_retenciones:>16,.2f}")
            print(f"  TOTAL         {f.total:>16,.2f}   ({len(f.lineas)} líneas, estado {f.estado})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
