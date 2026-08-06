"""
Caso de uso real UCASE-001 — ZULUPRINTS (importación marítima FCL Shenzhen → Buenaventura).

Reproduce en la base el caso documentado en `ucase-001/`:
  · Cliente ZULUPRINTS SAS
  · Naviera MSK (Maersk Line)
  · Conceptos faltantes del catálogo operativo
  · Operación que agrupa la cotización
  · Cotización UCC-5340426 con sus 16 rubros, en moneda mixta USD/COP

La TRM (3.735,71) es la que reproduce el total aproximado de $38.629.000 que el
correo comunicó al cliente.

NO crea las facturas: el caso las tiene (UC 1631 en USD y UC 1632 en COP) pero
se generan desde la cotización con el flujo normal.

Es idempotente: si la cotización ya existe, no hace nada.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_ucase_001
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.adm import AdmTercero
from app.models.admin import AdmTarifaIva, AdmUsuario
from app.models.contabilidad import CntCuenta
from app.models.ope import OpeAerolinea, OpeConcepto, OpeCotizacion, OpeCotizacionLinea, OpeOperacion
from app.services.ope_cotizacion_service import _generar_numero_cotizacion, _generar_numero_operacion

# La cotización se numera con el consecutivo del sistema; UCC-5340426 es la
# referencia del correo original y queda en las notas.
REFERENCIA_CLIENTE = "UCC-5340426"
DIAS_VIGENCIA = 15
TRM = Decimal("3735.71")

# Conceptos que faltan en el catálogo para poder cotizar este caso.
# (nombre, sección, tipo_cálculo, moneda, cuenta de ingreso, IVA 19%, es_valor_tercero)
CONCEPTOS_NUEVOS = [
    ("Recogida, aduana y consolidación en origen", "GASTOS_ORIGEN",        "POR_EMBARQUE", "USD", "414540", False, False),
    ("Licencia de exportación",                    "GASTOS_ORIGEN",        "POR_EMBARQUE", "USD", "414595", False, False),
    ("THCD",                                       "GASTOS_DESTINO",       "POR_EMBARQUE", "USD", "414530", True,  False),
    ("Documentación",                              "GASTOS_DESTINO",       "POR_EMBARQUE", "USD", "414595", True,  False),
    ("Manejo en destino",                          "GASTOS_DESTINO",       "POR_EMBARQUE", "USD", "414530", True,  False),
    ("Gastos en puerto",                           "ADUANA",               "POR_EMBARQUE", "COP", "281505", False, True),
    ("Transporte puerto a Bogotá",                 "TRANSPORTE_TERRESTRE", "POR_EMBARQUE", "COP", "414505", False, False),
    ("Devolución de contenedor vacío",             "TRANSPORTE_TERRESTRE", "POR_EMBARQUE", "COP", "414505", False, False),
    ("GPS",                                        "TRANSPORTE_TERRESTRE", "POR_EMBARQUE", "COP", "414540", True,  False),
]

# Las 16 líneas de la cotización, en el orden del correo.
# (concepto, sección, tipo_cálculo, moneda, valor_unitario, mínimo, total_venta)
LINEAS = [
    ("Flete internacional",                        "TRANSPORTE_INTERNACIONAL", "POR_EMBARQUE", "USD", "3200",   None,       "3200"),
    ("Recogida, aduana y consolidación en origen", "GASTOS_ORIGEN",            "POR_EMBARQUE", "USD", "2850",   None,       "2850"),
    ("Licencia de exportación",                    "GASTOS_ORIGEN",            "POR_EMBARQUE", "USD", "250",    None,       "250"),
    ("THCD",                                       "GASTOS_DESTINO",           "POR_EMBARQUE", "USD", "200",    None,       "200"),
    ("Documentación",                              "GASTOS_DESTINO",           "POR_EMBARQUE", "USD", "100",    None,       "100"),
    ("Manejo en destino",                          "GASTOS_DESTINO",           "POR_EMBARQUE", "USD", "70",     None,       "70"),
    # "COP 600.000 o 0,42% sobre valor CIF": porcentaje con mínimo. Sin CIF
    # declarado, aplica el mínimo — que es lo que el correo cotizó.
    ("Agenciamiento aduanero",                     "ADUANA",                   "PORCENTAJE",   "COP", "0.42",   "600000",   "600000"),
    ("Gastos operativos",                          "ADUANA",                   "POR_EMBARQUE", "COP", "300000", None,       "300000"),
    ("Elaboracion DIM y DAV",                      "ADUANA",                   "POR_EMBARQUE", "COP", "75000",  None,       "75000"),
    ("Gastos en puerto",                           "ADUANA",                   "POR_EMBARQUE", "COP", "1500000", None,      "1500000"),
    ("Almacenamiento",                             "ALMACENAMIENTO",           "POR_EMBARQUE", "COP", "2500000", None,      "2500000"),
    ("Transporte puerto a Bogotá",                 "TRANSPORTE_TERRESTRE",     "POR_EMBARQUE", "COP", "6400000", None,      "6400000"),
    ("Devolución de contenedor vacío",             "TRANSPORTE_TERRESTRE",     "POR_EMBARQUE", "COP", "1200000", None,      "1200000"),
    ("GPS",                                        "TRANSPORTE_TERRESTRE",     "POR_EMBARQUE", "COP", "250000", None,       "250000"),
    ("Urbano",                                     "TRANSPORTE_TERRESTRE",     "POR_EMBARQUE", "COP", "700000", None,       "700000"),
    # "USD 50 o 0,45% sobre valor de la mercancía": mismo patrón que el agenciamiento.
    ("Seguro internacional",                       "SEGURO",                   "PORCENTAJE",   "USD", "0.45",   "50",       "50"),
]

NOTAS = """Referencia del cliente: UCC-5340426 — Ruta Shenzhen (YANTIAN) → Buenaventura (BUN).
Tipo de operación: flete internacional FCL, gastos de liberación, OTM, aduana, almacenamiento y transporte local.
Carrier: MSK · Free days: 21 días.
Consolidado de 6 proveedores en origen, todos EXW con recogida a bodega:
  4) ZHENGZHOU CHAOKUO ELECTRONIC TECHNOLOGY CO., LTD — requiere licencia de exportación (CRD 21/abril)
  5) DONGGUAN DINGXING INDUSTRY CO., LTD
  6) NINGBO YIFAN OUTDOOR PRODUCTS CO., LTD.
Total aproximado comunicado al cliente: $38.629.000 (no incluye impuestos de importación).
El transporte puerto-Bogotá queda sujeto a revisión al momento del cargue."""


def _cuenta(db, codigo: str):
    return db.query(CntCuenta).filter(CntCuenta.codigo == codigo).first()


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(OpeCotizacion).filter(OpeCotizacion.notas.like(f"%{REFERENCIA_CLIENTE}%")).first():
            print(f"La cotización de referencia {REFERENCIA_CLIENTE} ya existe. Nada que hacer.")
            return

        from datetime import timedelta
        hoy = date.today()

        actor = db.query(AdmUsuario).first()
        iva19 = db.query(AdmTarifaIva).filter(AdmTarifaIva.nombre == "IVA 19%").first()

        # --- Cliente -------------------------------------------------------
        cliente = db.query(AdmTercero).filter(AdmTercero.nit == "830049009").first()
        if not cliente:
            cliente = AdmTercero(
                id=uuid.uuid4(), nit="830049009", digito_verif="9",
                razon_social="ZULUPRINTS SAS", tipo_persona="JURIDICA", tipo_tercero="CLIENTE",
                regimen="ORDINARIO", responsable_iva=True,
                telefono="(601) 6110893", direccion="CALLE 90 N 11 - 44 P6",
                municipio_codigo="11001", ciudad="Bogotá, D.C.", departamento="Bogotá, D.C.",
                pais="Colombia", pais_codigo="CO", tipo_documento_dian="31",
                creado_por=actor.id,
            )
            db.add(cliente)
            db.flush()
            print("Cliente ZULUPRINTS SAS creado.")
        else:
            print("Cliente ZULUPRINTS SAS ya existía.")

        # --- Naviera -------------------------------------------------------
        naviera = db.query(OpeAerolinea).filter(OpeAerolinea.nombre.ilike("%Maersk%")).first()
        if not naviera:
            naviera = OpeAerolinea(id=uuid.uuid4(), nombre="MSK — Maersk Line",
                                   codigo_iata="MSK", modalidad="MARITIMA", activo=True)
            db.add(naviera)
            db.flush()
            print("Naviera MSK creada.")

        # --- Conceptos faltantes -------------------------------------------
        nuevos = 0
        for nombre, seccion, tipo, moneda, cod_cuenta, con_iva, vrt in CONCEPTOS_NUEVOS:
            if db.query(OpeConcepto).filter(OpeConcepto.nombre == nombre).first():
                continue
            cta = _cuenta(db, cod_cuenta)
            db.add(OpeConcepto(
                id=uuid.uuid4(), nombre=nombre, seccion=seccion, tipo_calculo=tipo, moneda=moneda,
                cuenta_ingreso_id=cta.id if cta else None,
                tarifa_iva_id=iva19.id if (con_iva and iva19) else None,
                es_valor_tercero=vrt, creado_por=actor.id,
            ))
            nuevos += 1
        db.flush()
        print(f"Conceptos nuevos: {nuevos}")

        # --- Operación -----------------------------------------------------
        operacion = OpeOperacion(
            id=uuid.uuid4(), numero=_generar_numero_operacion(db, hoy), fecha_apertura=hoy,
            estado="EN_CURSO", aerolinea_id=naviera.id,
            piezas=71, peso_kg=Decimal("1049.05"), creado_por=actor.id,
        )
        db.add(operacion)
        db.flush()
        print(f"Operación {operacion.numero} creada.")

        # --- Cotización ----------------------------------------------------
        cot = OpeCotizacion(
            id=uuid.uuid4(), numero=_generar_numero_cotizacion(db, hoy), cliente_id=cliente.id,
            fecha=hoy, fecha_vigencia=hoy + timedelta(days=DIAS_VIGENCIA),
            tipo_operacion="IMPORTACION", modalidad="MARITIMA",
            origen="Shenzhen (YANTIAN), China", destino="Buenaventura (BUN), Colombia",
            aerolinea_id=naviera.id, incoterm="EXW",
            piezas=71, peso_kg=Decimal("1049.05"),
            moneda_mercancia="USD", trm=TRM,
            notas=NOTAS, estado="ENVIADA",
            asesor_id=actor.id, operacion_id=operacion.id,
            creado_por=actor.id,
        )
        db.add(cot)
        db.flush()

        for orden, (nombre, seccion, tipo, moneda, valor, minimo, total) in enumerate(LINEAS, start=1):
            concepto = db.query(OpeConcepto).filter(OpeConcepto.nombre == nombre).first()
            db.add(OpeCotizacionLinea(
                id=uuid.uuid4(), cotizacion_id=cot.id, seccion=seccion, orden=orden,
                concepto_id=concepto.id if concepto else None,
                descripcion=nombre, tipo_calculo=tipo,
                valor_unitario=Decimal(valor), costo_unitario=Decimal("0"),
                base=Decimal("1"), minimo=Decimal(minimo) if minimo else None,
                total_venta=Decimal(total), total_costo=Decimal("0"),
                moneda=moneda,
                valor_tercero=bool(concepto and concepto.es_valor_tercero),
            ))
        db.commit()

        usd = sum(Decimal(l[6]) for l in LINEAS if l[3] == "USD")
        cop = sum(Decimal(l[6]) for l in LINEAS if l[3] == "COP")
        print(f"Cotización {cot.numero} creada con {len(LINEAS)} líneas (ref. cliente {REFERENCIA_CLIENTE}).")
        print(f"  USD {usd:,.2f} × {TRM} = {usd * TRM:,.2f} COP")
        print(f"  COP {cop:,.2f}")
        print(f"  TOTAL {(usd * TRM + cop):,.2f} COP   (el correo comunicó ~38.629.000)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
