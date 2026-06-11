"""
Siembra el PUC colombiano hasta nivel de cuentas de 4 dígitos.
Subcuentas de 6 dígitos → seed_puc_subcuentas.py

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_puc
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.contabilidad import CntCuenta

SYSTEM_UUID_STR = "00000000-0000-0000-0000-000000000001"

# (codigo, nombre, naturaleza)
# nivel se deduce de len(codigo): 1→1, 2→2, 4→3, 6→4
PUC = [
    # ══════════════════════════════════════
    # CLASE 1 — ACTIVO
    # ══════════════════════════════════════
    ("1",    "ACTIVO",                                        "DEBITO"),
    ("11",   "DISPONIBLE",                                    "DEBITO"),
    ("1105", "Caja",                                          "DEBITO"),
    ("1110", "Bancos",                                        "DEBITO"),
    ("1115", "Remesas en tránsito",                           "DEBITO"),
    ("1120", "Cuentas de ahorro",                             "DEBITO"),
    ("1125", "Fondos",                                        "DEBITO"),
    ("12",   "INVERSIONES",                                   "DEBITO"),
    ("1205", "Inversiones en acciones",                       "DEBITO"),
    ("1210", "Inversiones en cuotas o partes de interés social","DEBITO"),
    ("1215", "Bonos",                                         "DEBITO"),
    ("1220", "Cédulas",                                       "DEBITO"),
    ("13",   "DEUDORES",                                      "DEBITO"),
    ("1305", "Clientes",                                      "DEBITO"),
    ("1310", "Cuentas corrientes comerciales",                "DEBITO"),
    ("1315", "Cuentas por cobrar a casa matriz",              "DEBITO"),
    ("1320", "Cuentas por cobrar a vinculados económicos",    "DEBITO"),
    ("1323", "Cuentas por cobrar a directores",               "DEBITO"),
    ("1325", "Cuentas por cobrar a socios y accionistas",     "DEBITO"),
    ("1328", "Aportes por cobrar",                            "DEBITO"),
    ("1330", "Anticipos y avances",                           "DEBITO"),
    ("1332", "Cuentas de operación conjunta",                 "DEBITO"),
    ("1335", "Depósitos",                                     "DEBITO"),
    ("1340", "Promesas de compra venta",                      "DEBITO"),
    ("1345", "Ingresos por cobrar",                           "DEBITO"),
    ("1350", "Retención sobre contratos",                     "DEBITO"),
    ("1355", "Anticipo de impuestos y contribuciones o saldos a favor","DEBITO"),
    ("1360", "Reclamaciones",                                 "DEBITO"),
    ("1365", "Cuentas por cobrar a trabajadores",             "DEBITO"),
    ("1370", "Préstamos a particulares",                      "DEBITO"),
    ("1380", "Deudores varios",                               "DEBITO"),
    ("1385", "Derechos de recompra de cartera negociada",     "DEBITO"),
    ("1390", "Deudas de difícil cobro",                       "DEBITO"),
    ("1399", "Provisiones",                                   "CREDITO"),
    ("14",   "INVENTARIOS",                                   "DEBITO"),
    ("1405", "Materias primas",                               "DEBITO"),
    ("1410", "Productos en proceso",                          "DEBITO"),
    ("1415", "Obras de construcción en curso",                "DEBITO"),
    ("1417", "Obras de urbanismo",                            "DEBITO"),
    ("1420", "Contratos en ejecución",                        "DEBITO"),
    ("1425", "Cultivos en desarrollo",                        "DEBITO"),
    ("1428", "Plantaciones agrícolas",                        "DEBITO"),
    ("1430", "Productos terminados",                          "DEBITO"),
    ("1435", "Mercancías no fabricadas por la empresa",       "DEBITO"),
    ("1440", "Bienes raíces para la venta",                   "DEBITO"),
    ("1445", "Semovientes",                                   "DEBITO"),
    ("1450", "Terrenos",                                      "DEBITO"),
    ("1455", "Materiales, repuestos y accesorios",            "DEBITO"),
    ("1460", "Envases y empaques",                            "DEBITO"),
    ("1465", "Inventarios en tránsito",                       "DEBITO"),
    ("1499", "Provisiones",                                   "CREDITO"),
    ("15",   "PROPIEDADES, PLANTA Y EQUIPO",                  "DEBITO"),
    ("1504", "Terrenos",                                      "DEBITO"),
    ("1506", "Materiales proyectos petroleros",               "DEBITO"),
    ("1508", "Construcciones en curso",                       "DEBITO"),
    ("1512", "Maquinaria y equipos en montaje",               "DEBITO"),
    ("1516", "Construcciones y edificaciones",                "DEBITO"),
    ("1520", "Maquinaria y equipo",                           "DEBITO"),
    ("1524", "Equipo de oficina",                             "DEBITO"),
    ("1528", "Equipo de computación y comunicación",          "DEBITO"),
    ("1532", "Equipo médico-científico",                      "DEBITO"),
    ("1536", "Equipo de hoteles y restaurantes",              "DEBITO"),
    ("1540", "Flota y equipo de transporte",                  "DEBITO"),
    ("1544", "Flota y equipo fluvial y/o marítimo",           "DEBITO"),
    ("1548", "Flota y equipo aéreo",                          "DEBITO"),
    ("1572", "Minas y canteras",                              "DEBITO"),
    ("1592", "Depreciación acumulada",                        "CREDITO"),
    ("1596", "Depreciación diferida",                         "CREDITO"),
    ("1597", "Amortización acumulada",                        "CREDITO"),
    ("1598", "Agotamiento acumulado",                         "CREDITO"),
    ("1599", "Provisiones",                                   "CREDITO"),
    ("16",   "INTANGIBLES",                                   "DEBITO"),
    ("1605", "Crédito mercantil",                             "DEBITO"),
    ("1610", "Marcas",                                        "DEBITO"),
    ("1615", "Patentes",                                      "DEBITO"),
    ("1620", "Concesiones y franquicias",                     "DEBITO"),
    ("1625", "Derechos",                                      "DEBITO"),
    ("1635", "Licencias",                                     "DEBITO"),
    ("17",   "DIFERIDOS",                                     "DEBITO"),
    ("1705", "Gastos pagados por anticipado",                  "DEBITO"),
    ("1710", "Cargos diferidos",                              "DEBITO"),
    ("18",   "OTROS ACTIVOS",                                 "DEBITO"),
    ("1805", "Bienes de arte y cultura",                      "DEBITO"),
    ("1820", "Bienes entregados en comodato",                 "DEBITO"),
    ("19",   "VALORIZACIONES",                                "DEBITO"),
    ("1905", "Terrenos",                                      "DEBITO"),
    ("1910", "Construcciones y edificaciones",                "DEBITO"),

    # ══════════════════════════════════════
    # CLASE 2 — PASIVO
    # ══════════════════════════════════════
    ("2",    "PASIVO",                                        "CREDITO"),
    ("21",   "OBLIGACIONES FINANCIERAS",                      "CREDITO"),
    ("2105", "Bancos nacionales",                             "CREDITO"),
    ("2110", "Bancos del exterior",                           "CREDITO"),
    ("2115", "Corporaciones financieras",                     "CREDITO"),
    ("2120", "Compañías de financiamiento comercial",         "CREDITO"),
    ("2125", "Corporaciones de ahorro y vivienda",            "CREDITO"),
    ("2130", "Entidades financieras del exterior",            "CREDITO"),
    ("2135", "Compromisos de recompra de inversiones negociadas","CREDITO"),
    ("2140", "Compromisos de recompra de cartera negociada",  "CREDITO"),
    ("2145", "Obligaciones gubernamentales",                  "CREDITO"),
    ("2195", "Otras obligaciones",                            "CREDITO"),
    ("22",   "PROVEEDORES",                                   "CREDITO"),
    ("2205", "Nacionales",                                    "CREDITO"),
    ("2210", "Del exterior",                                  "CREDITO"),
    ("2215", "Cuentas corrientes comerciales",                "CREDITO"),
    ("2220", "Casa matriz",                                   "CREDITO"),
    ("2225", "Compañías vinculadas",                          "CREDITO"),
    ("23",   "CUENTAS POR PAGAR",                             "CREDITO"),
    ("2305", "Cuentas corrientes comerciales",                "CREDITO"),
    ("2310", "A casa matriz",                                 "CREDITO"),
    ("2315", "A compañías vinculadas",                        "CREDITO"),
    ("2320", "A contratistas",                                "CREDITO"),
    ("2325", "A contratistas varios",                         "CREDITO"),
    ("2330", "Costos y gastos por pagar",                     "CREDITO"),
    ("2335", "Retenciones y aportes de nómina",               "CREDITO"),
    ("2340", "Instalamentos por pagar",                       "CREDITO"),
    ("2345", "Avances y anticipos recibidos",                 "CREDITO"),
    ("2350", "Depósitos recibidos",                           "CREDITO"),
    ("2355", "Deudas con accionistas o socios",               "CREDITO"),
    ("2357", "Deudas con directores",                         "CREDITO"),
    ("2360", "Dividendos o participaciones por pagar",        "CREDITO"),
    ("2365", "Retención en la fuente",                        "CREDITO"),
    ("2367", "Impuesto a las ventas retenido",                "CREDITO"),
    ("2368", "Impuesto de industria y comercio retenido",     "CREDITO"),
    ("2370", "Anticipos recibidos para ventas",               "CREDITO"),
    ("2375", "Impuesto sobre las ventas retenido",            "CREDITO"),
    ("2380", "Acreedores varios",                             "CREDITO"),
    ("24",   "IMPUESTOS, GRAVÁMENES Y TASAS",                 "CREDITO"),
    ("2404", "De renta y complementarios",                    "CREDITO"),
    ("2408", "Impuesto sobre las ventas por pagar",           "CREDITO"),
    ("2412", "De industria y comercio",                       "CREDITO"),
    ("2416", "A la propiedad raíz",                           "CREDITO"),
    ("2420", "Derechos sobre instrumentos públicos",          "CREDITO"),
    ("2436", "De vehículos",                                  "CREDITO"),
    ("2495", "Otros",                                         "CREDITO"),
    ("25",   "OBLIGACIONES LABORALES",                        "CREDITO"),
    ("2505", "Salarios por pagar",                            "CREDITO"),
    ("2510", "Cesantías consolidadas",                        "CREDITO"),
    ("2515", "Intereses sobre cesantías",                     "CREDITO"),
    ("2520", "Prima de servicios",                            "CREDITO"),
    ("2525", "Vacaciones consolidadas",                       "CREDITO"),
    ("2530", "Prestaciones extralegales",                     "CREDITO"),
    ("2532", "Pensiones por pagar",                           "CREDITO"),
    ("2535", "Cuotas partes pensiones de jubilación",         "CREDITO"),
    ("2540", "Indemnizaciones laborales",                     "CREDITO"),
    ("26",   "PASIVOS ESTIMADOS Y PROVISIONES",               "CREDITO"),
    ("2605", "Para costos y gastos",                          "CREDITO"),
    ("2610", "Para obligaciones fiscales",                    "CREDITO"),
    ("2615", "Para obligaciones laborales",                   "CREDITO"),
    ("2620", "Para demandas y litigios pendientes",           "CREDITO"),
    ("27",   "DIFERIDOS",                                     "CREDITO"),
    ("2705", "Ingresos recibidos por anticipado",             "CREDITO"),
    ("2710", "Créditos diferidos",                            "CREDITO"),
    ("28",   "OTROS PASIVOS",                                 "CREDITO"),
    ("2805", "Anticipos recibidos",                           "CREDITO"),
    ("2810", "Depósitos para uso y arrendamiento",            "CREDITO"),
    ("2815", "Ingresos recibidos para terceros",              "CREDITO"),
    ("29",   "BONOS Y PAPELES COMERCIALES",                   "CREDITO"),
    ("2905", "Bonos en circulación",                          "CREDITO"),

    # ══════════════════════════════════════
    # CLASE 3 — PATRIMONIO
    # ══════════════════════════════════════
    ("3",    "PATRIMONIO",                                    "CREDITO"),
    ("31",   "CAPITAL SOCIAL",                                "CREDITO"),
    ("3105", "Capital suscrito y pagado",                     "CREDITO"),
    ("3115", "Aportes sociales",                              "CREDITO"),
    ("3120", "Capital asignado",                              "CREDITO"),
    ("3130", "Capital de personas naturales",                 "CREDITO"),
    ("3135", "Aportes del Estado",                            "CREDITO"),
    ("3140", "Fondo social",                                  "CREDITO"),
    ("32",   "SUPERÁVIT DE CAPITAL",                          "CREDITO"),
    ("3205", "Prima en colocación de acciones",               "CREDITO"),
    ("3210", "Crédito mercantil",                             "CREDITO"),
    ("33",   "RESERVAS",                                      "CREDITO"),
    ("3305", "Reserva legal",                                 "CREDITO"),
    ("3315", "Reservas estatutarias",                         "CREDITO"),
    ("3320", "Reservas ocasionales",                          "CREDITO"),
    ("34",   "REVALORIZACIÓN DEL PATRIMONIO",                 "CREDITO"),
    ("3405", "Ajuste por inflación",                          "CREDITO"),
    ("36",   "RESULTADOS DEL EJERCICIO",                      "CREDITO"),
    ("3605", "Utilidad del ejercicio",                        "CREDITO"),
    ("3610", "Pérdida del ejercicio",                         "DEBITO"),
    ("37",   "RESULTADOS DE EJERCICIOS ANTERIORES",           "CREDITO"),
    ("3705", "Utilidades acumuladas",                         "CREDITO"),
    ("3710", "Pérdidas acumuladas",                           "DEBITO"),
    ("38",   "SUPERÁVIT POR VALORIZACIONES",                  "CREDITO"),
    ("3805", "Terrenos",                                      "CREDITO"),
    ("3810", "Construcciones y edificaciones",                "CREDITO"),

    # ══════════════════════════════════════
    # CLASE 4 — INGRESOS
    # ══════════════════════════════════════
    ("4",    "INGRESOS",                                      "CREDITO"),
    ("41",   "INGRESOS OPERACIONALES",                        "CREDITO"),
    ("4105", "Agricultura, ganadería, caza y silvicultura",   "CREDITO"),
    ("4110", "Pesca",                                         "CREDITO"),
    ("4115", "Explotación de minas y canteras",               "CREDITO"),
    ("4120", "Industrias manufactureras",                     "CREDITO"),
    ("4125", "Suministro de electricidad, gas y agua",        "CREDITO"),
    ("4130", "Construcción",                                  "CREDITO"),
    ("4135", "Comercio al por mayor y al por menor",          "CREDITO"),
    ("4140", "Hoteles y restaurantes",                        "CREDITO"),
    ("4145", "Transporte, almacenamiento y comunicaciones",   "CREDITO"),
    ("4150", "Actividad financiera",                          "CREDITO"),
    ("4155", "Actividades inmobiliarias, empresariales y de alquiler","CREDITO"),
    ("4160", "Enseñanza",                                     "CREDITO"),
    ("4165", "Servicios sociales y de salud",                 "CREDITO"),
    ("4170", "Otras actividades de servicios comunitarios, sociales y personales","CREDITO"),
    ("4175", "Devoluciones en ventas",                        "CREDITO"),
    ("4180", "Otros servicios",                               "CREDITO"),
    ("42",   "INGRESOS NO OPERACIONALES",                     "CREDITO"),
    ("4205", "Financieros",                                   "CREDITO"),
    ("4210", "Dividendos y participaciones",                  "CREDITO"),
    ("4215", "Indemnizaciones",                               "CREDITO"),
    ("4220", "Arrendamientos",                                "CREDITO"),
    ("4225", "Comisiones",                                    "CREDITO"),
    ("4230", "Honorarios",                                    "CREDITO"),
    ("4235", "Servicios",                                     "CREDITO"),
    ("4240", "Utilidad en venta de inversiones",              "CREDITO"),
    ("4245", "Utilidad en venta de propiedades, planta y equipo","CREDITO"),
    ("4250", "Recuperaciones",                                "CREDITO"),
    ("4295", "Diversas",                                      "CREDITO"),

    # ══════════════════════════════════════
    # CLASE 5 — GASTOS
    # ══════════════════════════════════════
    ("5",    "GASTOS",                                        "DEBITO"),
    ("51",   "GASTOS OPERACIONALES DE ADMINISTRACIÓN",        "DEBITO"),
    ("5105", "Gastos de personal",                            "DEBITO"),
    ("5110", "Honorarios",                                    "DEBITO"),
    ("5115", "Impuestos",                                     "DEBITO"),
    ("5120", "Arrendamientos",                                "DEBITO"),
    ("5125", "Contribuciones y afiliaciones",                 "DEBITO"),
    ("5130", "Seguros",                                       "DEBITO"),
    ("5135", "Servicios",                                     "DEBITO"),
    ("5140", "Gastos legales",                                "DEBITO"),
    ("5145", "Mantenimiento y reparaciones",                  "DEBITO"),
    ("5150", "Adecuación e instalación",                      "DEBITO"),
    ("5155", "Gastos de viaje",                               "DEBITO"),
    ("5160", "Depreciaciones",                                "DEBITO"),
    ("5165", "Amortizaciones",                                "DEBITO"),
    ("5170", "Provisiones",                                   "DEBITO"),
    ("5175", "Promoción y publicidad",                        "DEBITO"),
    ("5180", "Comisiones",                                    "DEBITO"),
    ("5185", "Pérdidas en venta y retiro de bienes",          "DEBITO"),
    ("5190", "Gastos extraordinarios",                        "DEBITO"),
    ("5195", "Diversos",                                      "DEBITO"),
    ("5199", "Provisiones",                                   "DEBITO"),
    ("52",   "GASTOS OPERACIONALES DE VENTAS",                "DEBITO"),
    ("5205", "Gastos de personal",                            "DEBITO"),
    ("5210", "Honorarios",                                    "DEBITO"),
    ("5215", "Impuestos",                                     "DEBITO"),
    ("5220", "Arrendamientos",                                "DEBITO"),
    ("5225", "Contribuciones y afiliaciones",                 "DEBITO"),
    ("5230", "Seguros",                                       "DEBITO"),
    ("5235", "Servicios",                                     "DEBITO"),
    ("5245", "Mantenimiento y reparaciones",                  "DEBITO"),
    ("5255", "Gastos de viaje",                               "DEBITO"),
    ("5260", "Depreciaciones",                                "DEBITO"),
    ("5265", "Amortización",                                  "DEBITO"),
    ("5270", "Provisiones",                                   "DEBITO"),
    ("5275", "Promoción y publicidad",                        "DEBITO"),
    ("5280", "Comisiones",                                    "DEBITO"),
    ("5295", "Gastos diversos",                               "DEBITO"),
    ("53",   "GASTOS NO OPERACIONALES",                       "DEBITO"),
    ("5305", "Financieros",                                   "DEBITO"),
    ("5310", "Pérdida en venta de inversiones",               "DEBITO"),
    ("5315", "Gastos extraordinarios",                        "DEBITO"),
    ("5325", "Donaciones",                                    "DEBITO"),
    ("5395", "Gastos diversos",                               "DEBITO"),
    ("54",   "IMPUESTO DE RENTA Y COMPLEMENTARIOS",           "DEBITO"),
    ("5405", "Impuesto de renta",                             "DEBITO"),

    # ══════════════════════════════════════
    # CLASE 6 — COSTOS DE VENTAS
    # ══════════════════════════════════════
    ("6",    "COSTOS DE VENTAS",                              "DEBITO"),
    ("61",   "COSTO DE VENTAS Y PRESTACIÓN DE SERVICIOS",     "DEBITO"),
    ("6105", "Agricultura, ganadería, caza y silvicultura",   "DEBITO"),
    ("6110", "Pesca",                                         "DEBITO"),
    ("6115", "Explotación de minas y canteras",               "DEBITO"),
    ("6120", "Industrias manufactureras",                     "DEBITO"),
    ("6125", "Suministro de electricidad, gas y agua",        "DEBITO"),
    ("6130", "Construcción",                                  "DEBITO"),
    ("6135", "Comercio al por mayor y al por menor",          "DEBITO"),
    ("6140", "Hoteles y restaurantes",                        "DEBITO"),
    ("6145", "Transporte, almacenamiento y comunicaciones",   "DEBITO"),
    ("6150", "Actividad financiera",                          "DEBITO"),
    ("6155", "Actividades inmobiliarias, empresariales y de alquiler","DEBITO"),
    ("6160", "Enseñanza",                                     "DEBITO"),
    ("6165", "Servicios sociales y de salud",                 "DEBITO"),
    ("6170", "Otras actividades de servicios comunitarios, sociales y personales","DEBITO"),

    # ══════════════════════════════════════
    # CLASE 7 — COSTOS DE PRODUCCIÓN
    # ══════════════════════════════════════
    ("7",    "COSTOS DE PRODUCCIÓN O DE OPERACIÓN",           "DEBITO"),
    ("71",   "MATERIA PRIMA",                                 "DEBITO"),
    ("7105", "Materiales directos",                           "DEBITO"),
    ("7110", "Materiales indirectos",                         "DEBITO"),
    ("72",   "MANO DE OBRA DIRECTA",                          "DEBITO"),
    ("7205", "Sueldos y salarios",                            "DEBITO"),
    ("7210", "Prestaciones sociales",                         "DEBITO"),
    ("73",   "COSTOS INDIRECTOS",                             "DEBITO"),
    ("7305", "Mano de obra indirecta",                        "DEBITO"),
    ("7310", "Depreciaciones",                                "DEBITO"),
    ("7315", "Amortizaciones",                                "DEBITO"),
    ("7325", "Arrendamientos",                                "DEBITO"),
    ("7330", "Seguros",                                       "DEBITO"),
    ("7335", "Servicios",                                     "DEBITO"),
    ("7340", "Mantenimiento y reparaciones",                  "DEBITO"),
    ("7350", "Combustibles y lubricantes",                    "DEBITO"),
    ("7395", "Otros costos indirectos",                       "DEBITO"),

    # ══════════════════════════════════════
    # CLASE 8 — CUENTAS DE ORDEN DEUDORAS
    # ══════════════════════════════════════
    ("8",    "CUENTAS DE ORDEN DEUDORAS",                     "DEBITO"),
    ("81",   "DEUDORAS",                                      "DEBITO"),
    ("8105", "Bienes y valores entregados en garantía",       "DEBITO"),
    ("8110", "Bienes y valores entregados en custodia",       "DEBITO"),
    ("8115", "Bienes y valores entregados en administración", "DEBITO"),
    ("8120", "Bienes y valores recibidos en garantía",        "DEBITO"),
    ("8125", "Bienes y valores recibidos en custodia",        "DEBITO"),
    ("8135", "Activos totalmente depreciados, agotados o amortizados","DEBITO"),
    ("8145", "Responsabilidades contingentes",                "DEBITO"),
    ("8160", "Activos castigados",                            "DEBITO"),
    ("8195", "Otras cuentas deudoras de orden",               "DEBITO"),
    ("89",   "DEUDORAS POR CONTRA",                           "CREDITO"),
    ("8905", "Bienes y valores entregados en garantía (contra)","CREDITO"),

    # ══════════════════════════════════════
    # CLASE 9 — CUENTAS DE ORDEN ACREEDORAS
    # ══════════════════════════════════════
    ("9",    "CUENTAS DE ORDEN ACREEDORAS",                   "CREDITO"),
    ("91",   "ACREEDORAS",                                    "CREDITO"),
    ("9105", "Bienes y valores entregados en garantía",       "CREDITO"),
    ("9110", "Bienes y valores entregados en custodia",       "CREDITO"),
    ("9195", "Otras cuentas acreedoras de orden",             "CREDITO"),
    ("99",   "ACREEDORAS POR CONTRA",                         "DEBITO"),
    ("9905", "Bienes y valores entregados en garantía (contra)","DEBITO"),
]


def nivel_from_codigo(codigo: str) -> int:
    n = len(codigo)
    if n == 1: return 1
    if n == 2: return 2
    if n <= 4: return 3
    if n <= 6: return 4
    return 5


def acepta_movimiento(codigo: str) -> bool:
    return len(codigo) >= 6


def run():
    import uuid
    db = SessionLocal()
    try:
        if db.query(CntCuenta).count() > 0:
            print("PUC ya sembrado. Omitiendo.")
            return

        system_id = uuid.UUID(SYSTEM_UUID_STR)
        mapa: dict[str, uuid.UUID] = {}

        def padre_codigo(codigo: str):
            n = len(codigo)
            if n == 1: return None
            if n == 2: return codigo[0]
            if n <= 4: return codigo[:2]
            if n <= 6: return codigo[:4]
            return codigo[:6]

        print(f"Sembrando {len(PUC)} cuentas PUC...")
        for codigo, nombre, naturaleza in PUC:
            padre_cod = padre_codigo(codigo)
            padre_id = mapa.get(padre_cod) if padre_cod else None
            cuenta = CntCuenta(
                codigo=codigo,
                nombre=nombre,
                nivel=nivel_from_codigo(codigo),
                naturaleza=naturaleza,
                acepta_movimiento=acepta_movimiento(codigo),
                padre_id=padre_id,
                creado_por=system_id,
            )
            db.add(cuenta)
            db.flush()
            mapa[codigo] = cuenta.id

        db.commit()
        print(f"PUC sembrado: {len(PUC)} cuentas.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    from app.core.database import SessionLocal
    run()
