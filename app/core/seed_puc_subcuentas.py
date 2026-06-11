"""
Siembra subcuentas de 6 dígitos del PUC colombiano.
Idempotente — salta las que ya existen.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_puc_subcuentas
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import uuid
from app.core.database import SessionLocal
from app.models.contabilidad import CntCuenta

SYSTEM_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# (codigo, nombre, naturaleza, padre_override)
# padre_override: código de 4 dígitos cuando el padre NO es codigo[:4]
SUBCUENTAS = [
    # ─── 11 DISPONIBLE ───────────────────────────────────
    ("110501", "Caja general",                               "DEBITO",  None),
    ("110502", "Cajas menores",                              "DEBITO",  None),
    ("111005", "Bancos moneda nacional",                     "DEBITO",  None),
    ("111010", "Bancos moneda extranjera",                   "DEBITO",  None),
    ("112005", "Cuentas de ahorro moneda nacional",          "DEBITO",  None),
    ("112010", "Cuentas de ahorro moneda extranjera",        "DEBITO",  None),

    # ─── 13 DEUDORES ─────────────────────────────────────
    ("130505", "Clientes nacionales",                        "DEBITO",  None),
    ("130510", "Clientes del exterior",                      "DEBITO",  None),
    ("133005", "Anticipos a proveedores",                    "DEBITO",  None),
    ("133010", "Anticipos a empleados",                      "DEBITO",  None),
    ("133015", "Anticipos a contratistas",                   "DEBITO",  None),
    ("135005", "Retención sobre contratos",                  "DEBITO",  None),
    ("135505", "Anticipo IVA",                               "DEBITO",  None),
    ("135510", "Anticipo impuesto de renta",                 "DEBITO",  None),
    ("135515", "Anticipo impuesto de industria y comercio",  "DEBITO",  None),
    ("136505", "Préstamos a trabajadores",                   "DEBITO",  None),
    ("138005", "Deudores en litigio",                        "DEBITO",  None),
    ("138010", "Depósitos en garantía",                      "DEBITO",  None),
    ("139905", "Provisión deudores clientes",                "CREDITO", "1399"),

    # ─── 14 INVENTARIOS ──────────────────────────────────
    ("140501", "Materias primas",                            "DEBITO",  None),
    ("141001", "Productos en proceso",                       "DEBITO",  None),
    ("142001", "Productos terminados",                       "DEBITO",  "1430"),  # padre real: 1430
    ("143001", "Mercancías para la venta",                   "DEBITO",  "1435"),  # padre real: 1435
    ("146505", "Inventarios en tránsito nacional",           "DEBITO",  "1465"),

    # ─── 15 PROPIEDADES, PLANTA Y EQUIPO ─────────────────
    ("150405", "Terrenos urbanos",                           "DEBITO",  None),
    ("151205", "Maquinaria y equipo",                        "DEBITO",  "1520"),  # padre real: 1520
    ("151605", "Muebles y enseres",                          "DEBITO",  "1524"),  # padre real: 1524
    ("151610", "Equipo de oficina",                          "DEBITO",  "1524"),  # padre real: 1524
    ("152005", "Equipos de computación",                     "DEBITO",  "1528"),  # padre real: 1528
    ("152010", "Software y licencias",                       "DEBITO",  "1528"),  # padre real: 1528
    ("153205", "Vehículos",                                  "DEBITO",  "1540"),  # padre real: 1540
    ("153210", "Motos",                                      "DEBITO",  "1540"),  # padre real: 1540
    ("159205", "Depreciación muebles y enseres",             "CREDITO", None),
    ("159210", "Depreciación equipo de oficina",             "CREDITO", None),
    ("159215", "Depreciación equipo de computación",         "CREDITO", None),
    ("159220", "Depreciación vehículos",                     "CREDITO", None),
    ("159225", "Depreciación maquinaria y equipo",           "CREDITO", None),

    # ─── 17 DIFERIDOS ────────────────────────────────────
    ("170505", "Seguros pagados por anticipado",             "DEBITO",  None),
    ("170510", "Arrendamientos pagados por anticipado",      "DEBITO",  None),
    ("170515", "Intereses pagados por anticipado",           "DEBITO",  None),

    # ═══════════════════════════════════════════════════
    # CLASE 2 — PASIVO
    # ═══════════════════════════════════════════════════

    # ─── 21 OBLIGACIONES FINANCIERAS ─────────────────────
    ("210505", "Sobregiros bancarios",                       "CREDITO", None),
    ("210510", "Créditos de tesorería",                      "CREDITO", None),
    ("210515", "Créditos ordinarios",                        "CREDITO", None),
    ("210520", "Créditos de consumo",                        "CREDITO", None),
    ("210525", "Cartas de crédito",                          "CREDITO", None),

    # ─── 22 PROVEEDORES ──────────────────────────────────
    ("220505", "Proveedores nacionales",                     "CREDITO", None),
    ("220510", "Proveedores del exterior",                   "CREDITO", None),
    ("221005", "Del exterior",                               "CREDITO", None),

    # ─── 23 CUENTAS POR PAGAR ────────────────────────────
    ("233005", "Retención en la fuente practicada",          "CREDITO", "2330"),
    ("233010", "Retención de ICA",                           "CREDITO", "2330"),
    ("233015", "Retención de IVA",                           "CREDITO", "2330"),
    ("233505", "Aportes a salud empleados",                  "CREDITO", "2335"),
    ("233510", "Aportes a pensión empleados",                "CREDITO", "2335"),
    ("233515", "Aportes ARL",                                "CREDITO", "2335"),
    ("233520", "Aportes a salud empresa",                    "CREDITO", "2335"),
    ("233525", "Aportes a pensión empresa",                  "CREDITO", "2335"),
    ("233530", "Aportes SENA",                               "CREDITO", "2335"),
    ("233535", "Aportes ICBF",                               "CREDITO", "2335"),
    ("233540", "Aportes caja de compensación",               "CREDITO", "2335"),
    # 2365 Retención en la fuente
    ("236505", "Salarios y pagos laborales",                 "CREDITO", None),
    ("236510", "Dividendos y/o participaciones",             "CREDITO", None),
    ("236515", "Honorarios",                                 "CREDITO", None),
    ("236520", "Comisiones",                                 "CREDITO", None),
    ("236525", "Servicios",                                  "CREDITO", None),
    ("236530", "Arrendamientos",                             "CREDITO", None),
    ("236535", "Rendimientos financieros",                   "CREDITO", None),
    ("236540", "Compras",                                    "CREDITO", None),
    ("236570", "Otras retenciones y patrimonio",             "CREDITO", None),
    ("236575", "Autorretenciones",                           "CREDITO", None),
    # Costos y gastos por pagar (2330)
    ("231505", "Servicios por pagar",                        "CREDITO", "2330"),
    ("231510", "Honorarios por pagar",                       "CREDITO", "2330"),
    ("231515", "Comisiones por pagar",                       "CREDITO", "2330"),
    ("231520", "Arrendamientos por pagar",                   "CREDITO", "2330"),
    # Acreedores varios (2380)
    ("238005", "Acreedores varios",                          "CREDITO", "2380"),

    # ─── 24 IMPUESTOS ────────────────────────────────────
    ("240405", "Impuesto de renta corriente",                "CREDITO", None),
    ("240410", "Impuesto de renta diferido",                 "CREDITO", None),
    ("240805", "IVA por pagar",                              "CREDITO", None),
    ("240810", "IVA descontable en compras",                 "DEBITO",  None),
    ("241205", "ICA por pagar",                              "CREDITO", None),
    ("241605", "Impuesto predial",                           "CREDITO", None),

    # ─── 25 OBLIGACIONES LABORALES ───────────────────────
    ("250505", "Salarios por pagar",                         "CREDITO", None),
    ("251005", "Cesantías consolidadas",                     "CREDITO", None),
    ("251505", "Intereses sobre cesantías",                  "CREDITO", None),
    ("252005", "Prima de servicios",                         "CREDITO", None),
    ("252505", "Vacaciones consolidadas",                    "CREDITO", None),

    # ─── 27 DIFERIDOS ────────────────────────────────────
    ("270505", "Ingresos recibidos por anticipado",          "CREDITO", None),

    # ═══════════════════════════════════════════════════
    # CLASE 3 — PATRIMONIO
    # ═══════════════════════════════════════════════════
    ("310505", "Capital autorizado",                         "CREDITO", None),
    ("310510", "Capital por suscribir",                      "DEBITO",  None),
    ("311505", "Aportes sociales",                           "CREDITO", "3115"),
    ("330505", "Reserva legal apropiada",                    "CREDITO", None),
    ("330510", "Reserva legal no apropiada",                 "CREDITO", None),
    ("331505", "Reservas estatutarias",                      "CREDITO", None),
    ("360505", "Utilidad del ejercicio",                     "CREDITO", None),
    ("361005", "Pérdida del ejercicio",                      "DEBITO",  None),
    ("370505", "Utilidades acumuladas",                      "CREDITO", None),
    ("371005", "Pérdidas acumuladas",                        "DEBITO",  None),

    # ═══════════════════════════════════════════════════
    # CLASE 4 — INGRESOS
    # ═══════════════════════════════════════════════════
    # 4110 Pesca
    ("411005", "Actividad de pesca",                         "CREDITO", None),
    ("411010", "Explotación de criaderos de peces",          "CREDITO", None),
    ("411015", "Actividades conexas",                        "CREDITO", None),
    # 4145 Transporte, almacenamiento y comunicaciones
    ("414505", "Servicio de transporte por carretera",       "CREDITO", None),
    ("414510", "Servicio de transporte por vía férrea",      "CREDITO", None),
    ("414515", "Servicio de transporte por vía acuática",    "CREDITO", None),
    ("414520", "Servicio de transporte por vía aérea",       "CREDITO", None),
    ("414530", "Manipulación de carga",                      "CREDITO", None),
    ("414535", "Almacenamiento y depósito",                  "CREDITO", None),
    ("414540", "Servicios complementarios para el transporte","CREDITO", None),
    ("414545", "Agencias de viaje",                          "CREDITO", None),
    ("414550", "Otras agencias de transporte",               "CREDITO", None),
    ("414595", "Actividades conexas",                        "CREDITO", None),
    # 4180 Otros servicios
    ("418005", "Servicios prestados",                        "CREDITO", None),
    # 42 Ingresos no operacionales
    ("420505", "Intereses recibidos",                        "CREDITO", None),
    ("420510", "Rendimientos financieros",                   "CREDITO", None),
    ("420515", "Descuentos financieros obtenidos",           "CREDITO", None),
    ("422005", "Arrendamientos recibidos",                   "CREDITO", None),
    ("425005", "Recuperación de provisiones",                "CREDITO", None),
    ("429505", "Ingresos por diferencia en cambio",          "CREDITO", None),

    # ═══════════════════════════════════════════════════
    # CLASE 5 — GASTOS ADMINISTRACIÓN
    # ═══════════════════════════════════════════════════
    ("510506", "Sueldos y salarios administración",          "DEBITO",  None),
    ("510527", "Auxilio de transporte",                      "DEBITO",  None),
    ("510530", "Cesantías",                                  "DEBITO",  None),
    ("510533", "Intereses sobre cesantías",                  "DEBITO",  None),
    ("510536", "Prima de servicios",                         "DEBITO",  None),
    ("510539", "Vacaciones",                                 "DEBITO",  None),
    ("510545", "Dotación y suministro",                      "DEBITO",  None),
    ("510548", "Aportes a salud",                            "DEBITO",  None),
    ("510551", "Aportes a pensión",                          "DEBITO",  None),
    ("510554", "Aportes ARL",                                "DEBITO",  None),
    ("510557", "Aportes SENA",                               "DEBITO",  None),
    ("510560", "Aportes ICBF",                               "DEBITO",  None),
    ("510563", "Caja de compensación",                       "DEBITO",  None),
    ("511005", "Honorarios a personas naturales",            "DEBITO",  None),
    ("511010", "Honorarios a personas jurídicas",            "DEBITO",  None),
    ("511505", "Predial unificado",                          "DEBITO",  None),
    ("511510", "Industria y comercio",                       "DEBITO",  None),
    ("511515", "Vehículos",                                  "DEBITO",  None),
    ("511520", "Gravamen movimientos financieros",           "DEBITO",  None),
    ("512005", "Arrendamiento inmuebles",                    "DEBITO",  None),
    ("512010", "Arrendamiento maquinaria",                   "DEBITO",  None),
    ("512015", "Arrendamiento equipo",                       "DEBITO",  None),
    ("513005", "Seguros de incendio",                        "DEBITO",  None),
    ("513010", "Seguros de vida",                            "DEBITO",  None),
    ("513015", "Seguros de vehículos",                       "DEBITO",  None),
    ("513020", "Seguros de manejo",                          "DEBITO",  None),
    ("513505", "Energía eléctrica",                          "DEBITO",  None),
    ("513510", "Gas",                                        "DEBITO",  None),
    ("513515", "Teléfono",                                   "DEBITO",  None),
    ("513520", "Internet y datos",                           "DEBITO",  None),
    ("513525", "Correo y mensajería",                        "DEBITO",  None),
    ("513530", "Aseo y vigilancia",                          "DEBITO",  None),
    ("513535", "Transporte y acarreo",                       "DEBITO",  None),
    ("513540", "Servicios de software (SaaS)",               "DEBITO",  None),
    ("514505", "Mantenimiento construcciones",               "DEBITO",  None),
    ("514510", "Mantenimiento maquinaria y equipo",          "DEBITO",  None),
    ("514515", "Mantenimiento equipo de cómputo",            "DEBITO",  None),
    ("514520", "Mantenimiento vehículos",                    "DEBITO",  None),
    ("515505", "Pasajes aéreos y terrestres",                "DEBITO",  None),
    ("515510", "Alojamiento",                                "DEBITO",  None),
    ("515515", "Manutención",                                "DEBITO",  None),
    ("516005", "Depreciación muebles y enseres",             "DEBITO",  None),
    ("516010", "Depreciación equipo de oficina",             "DEBITO",  None),
    ("516015", "Depreciación equipo de cómputo",             "DEBITO",  None),
    ("516020", "Depreciación vehículos",                     "DEBITO",  None),
    ("516025", "Depreciación maquinaria y equipo",           "DEBITO",  None),
    ("519505", "Útiles, papelería y fotocopias",             "DEBITO",  None),
    ("519510", "Cafetería y restaurante",                    "DEBITO",  None),
    ("519515", "Elementos de aseo y limpieza",               "DEBITO",  None),
    ("519520", "Casino y restaurante empleados",             "DEBITO",  None),
    ("519525", "Parqueadero",                                "DEBITO",  None),

    # ─── GASTOS VENTAS ───────────────────────────────────
    ("520506", "Sueldos y salarios ventas",                  "DEBITO",  None),
    ("520527", "Auxilio de transporte ventas",               "DEBITO",  None),
    ("520530", "Cesantías ventas",                           "DEBITO",  None),
    ("520548", "Aportes a salud ventas",                     "DEBITO",  None),
    ("520551", "Aportes a pensión ventas",                   "DEBITO",  None),
    ("527505", "Publicidad en medios",                       "DEBITO",  None),
    ("527510", "Material publicitario",                      "DEBITO",  None),
    ("527515", "Ferias y exposiciones",                      "DEBITO",  None),
    ("528005", "Comisiones a vendedores",                    "DEBITO",  None),
    ("529505", "Gastos de representación",                   "DEBITO",  None),

    # ─── GASTOS NO OPERACIONALES ─────────────────────────
    ("530505", "Intereses bancarios",                        "DEBITO",  None),
    ("530510", "Comisiones bancarias",                       "DEBITO",  None),
    ("530515", "Gravamen movimientos financieros",           "DEBITO",  None),
    ("530520", "Diferencia en cambio",                       "DEBITO",  None),

    # ═══════════════════════════════════════════════════
    # CLASE 6 — COSTOS DE VENTAS
    # ═══════════════════════════════════════════════════
    ("611005", "Actividad de pesca",                         "DEBITO",  None),
    ("611010", "Explotación de criaderos de peces",          "DEBITO",  None),
    ("611015", "Actividades conexas",                        "DEBITO",  None),
    ("611020", "Otros ingresos de pesca",                    "DEBITO",  None),
    ("611025", "Fletes en adquisición",                      "DEBITO",  None),
    ("611030", "Costos complementarios de pesca",            "DEBITO",  None),
    ("614505", "Servicio de transporte por carretera",       "DEBITO",  None),
    ("614510", "Servicio de transporte por vía férrea",      "DEBITO",  None),
    ("614515", "Servicio de transporte por vía acuática",    "DEBITO",  None),
    ("614520", "Servicio de transporte por vía aérea",       "DEBITO",  None),
    ("614530", "Manipulación de carga",                      "DEBITO",  None),
    ("614535", "Almacenamiento y depósito",                  "DEBITO",  None),
    ("614540", "Servicios complementarios para el transporte","DEBITO",  None),
    ("614545", "Agencias de viaje",                          "DEBITO",  None),
    ("614550", "Otras agencias de transporte",               "DEBITO",  None),
    ("614595", "Actividades conexas",                        "DEBITO",  None),

    # ═══════════════════════════════════════════════════
    # CLASE 7 — COSTOS DE PRODUCCIÓN
    # ═══════════════════════════════════════════════════
    ("710505", "Materias primas consumidas",                 "DEBITO",  None),
    ("711005", "Materiales indirectos",                      "DEBITO",  None),
    ("720505", "Salarios mano de obra directa",              "DEBITO",  None),
    ("720510", "Prestaciones mano de obra directa",          "DEBITO",  None),
    ("730505", "Salarios mano de obra indirecta",            "DEBITO",  None),
    ("731005", "Depreciación maquinaria producción",         "DEBITO",  None),
    ("733505", "Servicios planta producción",                "DEBITO",  None),
    ("735005", "Combustibles y lubricantes",                 "DEBITO",  None),
]


def nivel_from_codigo(codigo: str) -> int:
    n = len(codigo)
    if n == 1: return 1
    if n == 2: return 2
    if n <= 4: return 3
    if n <= 6: return 4
    return 5


def run():
    db = SessionLocal()
    try:
        existentes = {c.codigo: c for c in db.query(CntCuenta).all()}
        creadas = 0

        for row in SUBCUENTAS:
            codigo, nombre, naturaleza = row[0], row[1], row[2]
            padre_override = row[3] if len(row) > 3 else None

            if codigo in existentes:
                continue

            padre_cod = padre_override if padre_override else codigo[:4]
            padre = existentes.get(padre_cod)
            if not padre:
                print(f"  [!] Padre {padre_cod} no encontrado para {codigo} — omitido")
                continue

            cuenta = CntCuenta(
                codigo=codigo,
                nombre=nombre,
                nivel=nivel_from_codigo(codigo),
                naturaleza=naturaleza,
                acepta_movimiento=True,
                padre_id=padre.id,
                creado_por=SYSTEM_UUID,
            )
            db.add(cuenta)
            db.flush()
            existentes[codigo] = cuenta
            creadas += 1

        db.commit()
        print(f"Subcuentas creadas: {creadas}")
        print("Seed completado.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    from app.core.database import SessionLocal
    run()
