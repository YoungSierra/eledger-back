"""
Seed de datos demo para el módulo operativo (ope_).

Crea clientes, contrapartes del exterior, cotizaciones en los cinco estados y
operaciones en los cuatro estados, con su carpeta documental (MAWB, HAWBs y
manifiesto), para que las listas y el dashboard tengan volumen realista en dev.

Todo lo que crea queda marcado con MARCA_DEMO en `notas`, de modo que se puede
retirar sin tocar los datos reales ya cargados.

No usa INSERT crudos: pasa por los services para que los consecutivos, la
máquina de estados y la auditoría queden como en producción. Dos excepciones
deliberadas, ambas para poder situar los datos en el pasado:

  - `fecha_vigencia` se retrocede después de las transiciones de estado, porque
    el service vence automáticamente toda cotización BORRADOR/ENVIADA con
    vigencia pasada, y lo hace dentro de obtener_cotizacion(), o sea antes de
    validar el estado en enviar/aprobar/rechazar.
  - `fecha_apertura` y `estado` de la operación se ajustan al final, porque
    aprobar_cotizacion() siempre abre la operación hoy y en ABIERTA.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_ope_demo
    venv\\Scripts\\python -m app.core.seed_ope_demo --limpiar
"""
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.adm import AdmTercero
from app.models.admin import AdmUsuario
from app.models.ope import (
    OpeAerolinea, OpeAeropuerto, OpeConcepto, OpeCotizacion, OpeCotizacionLinea,
    OpeManifiesto, OpeManifiestoLinea, OpeMawb, OpeHawb, OpeOperacion,
)
from app.schemas.auth import UsuarioActual
from app.schemas.ope import (
    OpeCotizacionCreate, OpeCotizacionLineaCreate,
    OpeHawbCreate, OpeHawbUpdate, OpeMawbCreate, OpeMawbUpdate,
    OpeManifiestoCreate, OpeManifiestoLineaCreate,
)
from app.services import ope_cotizacion_service as svc
from app.services import ope_operacion_service as ops_svc

MARCA_DEMO = "[DEMO]"

# ---------------------------------------------------------------------------
# Catálogo de aeropuertos que las rutas demo necesitan.
# No lleva marca demo: son aeropuertos reales y --limpiar no los borra.
# ---------------------------------------------------------------------------

AEROPUERTOS = [
    ("CLO", "Aeropuerto Internacional Alfonso Bonilla Aragón", "Cali",       "Colombia"),
    ("MDE", "Aeropuerto Internacional José María Córdova",     "Medellín",   "Colombia"),
    ("MIA", "Miami International Airport",                     "Miami",      "EEUU"),
    ("MAD", "Aeropuerto Adolfo Suárez Madrid-Barajas",         "Madrid",     "España"),
    ("FRA", "Frankfurt am Main Airport",                       "Fráncfort",  "Alemania"),
    ("PVG", "Shanghai Pudong International Airport",           "Shanghái",   "China"),
    ("PTY", "Aeropuerto Internacional de Tocumen",             "Panamá",     "Panamá"),
    ("TLV", "Ben Gurion International Airport",                "Tel Aviv",   "Israel"),
]

# ciudad (como se escribe en origen/destino) -> (IATA, nit de la contraparte)
# Las ciudades colombianas no tienen contraparte: ahí va el cliente.
CIUDADES = {
    "BOGOTA":       ("BOG", None),
    "CALI":         ("CLO", None),
    "MEDELLIN":     ("MDE", None),
    "MIAMI":        ("MIA", "EXT-US-9001"),
    "NEW YORK":     ("JFK", "EXT-US-9002"),
    "SHANGHAI":     ("PVG", "EXT-CN-9003"),
    "MADRID":       ("MAD", "EXT-ES-9004"),
    "FRANKFURT":    ("FRA", "EXT-DE-9005"),
    "PANAMA":       ("PTY", "EXT-PA-9006"),
    "TEL AVIV":     ("TLV", "EXT-IL-9007"),
    "SAN SALVADOR": ("SAL", "EXT-SV-9008"),
}

# ---------------------------------------------------------------------------
# Terceros demo
# ---------------------------------------------------------------------------

CLIENTES = [
    ("901234567", "COMERCIALIZADORA ANDINA DEL PACIFICO S.A.S", "Bogotá",   "Cundinamarca"),
    ("900876543", "TEXTILES DEL NORTE LTDA",                    "Medellín", "Antioquia"),
    ("901456789", "IMPORTACIONES GARCIA HERMANOS S.A.S",        "Cali",     "Valle del Cauca"),
    ("830112233", "DISTRIBUIDORA FARMACEUTICA CIMPA S.A.S",     "Bogotá",   "Cundinamarca"),
    ("901987654", "AGROEXPORTADORA VALLE VERDE S.A.S",          "Cali",     "Valle del Cauca"),
]

# Contrapartes del exterior: shipper en importación, consignee en exportación.
CONTRAPARTES = [
    ("EXT-US-9001", "GLOBAL FREIGHT SOLUTIONS INC",     "Miami",        "Estados Unidos"),
    ("EXT-US-9002", "MERIDIAN SHIPPING LLC",            "Nueva York",   "Estados Unidos"),
    ("EXT-CN-9003", "SHANGHAI EASTERN TRADING CO LTD",  "Shanghái",     "China"),
    ("EXT-ES-9004", "IBERIA CARGO LOGISTICS S.L.",      "Madrid",       "España"),
    ("EXT-DE-9005", "RHEIN CARGO GMBH",                 "Fráncfort",    "Alemania"),
    ("EXT-PA-9006", "LOGISTICA ISTMO PANAMA S.A.",      "Panamá",       "Panamá"),
    ("EXT-IL-9007", "LEVANT TRADE LTD",                 "Tel Aviv",     "Israel"),
    ("EXT-SV-9008", "CENTROAMERICA CARGO SA DE CV",     "San Salvador", "El Salvador"),
]


def _digito_verificacion(nit: str) -> str:
    """DV según algoritmo DIAN."""
    pesos = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    total = sum(int(d) * pesos[i] for i, d in enumerate(reversed(nit)))
    resto = total % 11
    return str(resto if resto <= 1 else 11 - resto)


# ---------------------------------------------------------------------------
# Cotizaciones demo
#   (cliente_idx, tipo, origen, destino, piezas, peso, valor_cif_usd,
#    aerolinea_iata, estado, dias_atras)
# ---------------------------------------------------------------------------

COTIZACIONES = [
    (0, "IMPORTACION", "MIAMI",     "BOGOTA",       4,  620,  48000, "AA", "APROBADA",  54),
    (1, "IMPORTACION", "SHANGHAI",  "BOGOTA",      12, 1840,  96000, "LH", "APROBADA",  49),
    (2, "IMPORTACION", "NEW YORK",  "CALI",         3,  410,  31500, "AV", "APROBADA",  45),
    (3, "IMPORTACION", "MADRID",    "BOGOTA",       6,  980,  72000, "AV", "APROBADA",  41),
    (4, "EXPORTACION", "BOGOTA",    "MIAMI",        8, 1250,  54000, "AA", "APROBADA",  38),
    (0, "IMPORTACION", "PANAMA",    "BOGOTA",       2,  185,  14200, "CM", "APROBADA",  33),
    (1, "EXPORTACION", "MEDELLIN",  "NEW YORK",     5,  760,  41000, "AV", "APROBADA",  27),
    (2, "IMPORTACION", "FRANKFURT", "MEDELLIN",     9, 1420,  88000, "LH", "APROBADA",  20),
    (3, "IMPORTACION", "MIAMI",     "BOGOTA",       3,  340,  26500, "AA", "APROBADA",  13),
    (4, "EXPORTACION", "CALI",      "PANAMA",       7,  890,  38000, "CM", "APROBADA",   6),

    (0, "IMPORTACION", "TEL AVIV",  "BOGOTA",       2,  260,  22000, "LA", "ENVIADA",    9),
    (1, "IMPORTACION", "MIAMI",     "BOGOTA",       5,  710,  45000, "AA", "ENVIADA",    7),
    (2, "EXPORTACION", "BOGOTA",    "MADRID",       4,  530,  33000, "AV", "ENVIADA",    5),
    (3, "IMPORTACION", "SHANGHAI",  "CALI",        14, 2100, 110000, "LH", "ENVIADA",    3),
    (4, "EXPORTACION", "BOGOTA",    "SAN SALVADOR", 6,  820,  40000, "CM", "ENVIADA",    1),

    (0, "IMPORTACION", "NEW YORK",  "BOGOTA",       3,  395,  29000, "AV", "BORRADOR",   4),
    (1, "EXPORTACION", "MEDELLIN",  "MIAMI",        9, 1180,  61000, "AA", "BORRADOR",   2),
    (2, "IMPORTACION", "MADRID",    "BOGOTA",       2,  240,  19500, "LH", "BORRADOR",   1),
    (3, "IMPORTACION", "PANAMA",    "MEDELLIN",     4,  505,  35000, "CM", "BORRADOR",   0),

    (4, "IMPORTACION", "MIAMI",     "CALI",         6,  865,  52000, "AA", "RECHAZADA", 30),
    (0, "EXPORTACION", "BOGOTA",    "TEL AVIV",     3,  370,  28000, "LA", "RECHAZADA", 22),
    (1, "IMPORTACION", "FRANKFURT", "BOGOTA",      11, 1650,  94000, "LH", "RECHAZADA", 11),

    (2, "IMPORTACION", "SHANGHAI",  "BOGOTA",       8, 1240,  67000, "LH", "VENCIDA",   50),
    (3, "EXPORTACION", "BOGOTA",    "NEW YORK",     5,  680,  36000, "AV", "VENCIDA",   43),
]

# Las 10 operaciones que nacen de las cotizaciones APROBADA, en el mismo orden.
#   (estado, dias_atras_apertura, num_hawbs, con_manifiesto)
# Una operación recién abierta todavía no tiene carpeta documental; una cerrada
# la tiene completa.
OPERACIONES = [
    ("CERRADA",   53, 3, True),
    ("CERRADA",   48, 2, True),
    ("EN_CURSO",  44, 2, True),
    ("EN_CURSO",  40, 1, True),
    ("EN_CURSO",  37, 2, False),
    ("CANCELADA", 32, 0, False),
    ("EN_CURSO",  26, 1, True),
    ("ABIERTA",   19, 1, False),
    ("ABIERTA",   12, 0, False),
    ("ABIERTA",    5, 0, False),
]

# Prefijo IATA de guía madre por aerolínea.
PREFIJO_MAWB = {"AV": "134", "AA": "001", "LA": "045", "CM": "230", "LH": "020", "5Y": "369"}

# (nombre_concepto, valor_unitario_venta, costo_unitario)
PLANTILLA_LINEAS = [
    ("Flete internacional",    Decimal("2.80"),   Decimal("2.10")),
    ("AWB",                    Decimal("45"),     Decimal("35")),
    ("Manejo",                 Decimal("60"),     Decimal("42")),
    ("ATF",                    Decimal("0.18"),   Decimal("0.12")),
    ("Handling",               Decimal("85"),     Decimal("60")),
    ("Agenciamiento aduanero", Decimal("0.65"),   Decimal("0.40")),
    ("Gastos operativos",      Decimal("180000"), Decimal("120000")),
    ("Urbano",                 Decimal("320000"), Decimal("240000")),
    ("Seguro internacional",   Decimal("0.35"),   Decimal("0.22")),
]

TRM_BASE = Decimal("3620")

MERCANCIAS = [
    "Repuestos industriales", "Textiles y confecciones", "Equipos de cómputo",
    "Productos farmacéuticos", "Flores frescas cortadas", "Maquinaria agrícola",
    "Insumos plásticos", "Café verde en sacos",
]


def _actor(db: Session) -> UsuarioActual:
    u = (
        db.query(AdmUsuario)
        .filter(AdmUsuario.activo == True, AdmUsuario.tercero_id.is_(None))
        .order_by(AdmUsuario.creado_en)
        .first()
    )
    if not u:
        print("ERROR: no hay usuario interno activo para atribuir el seed.")
        sys.exit(1)
    return UsuarioActual(
        id=str(u.id), email=u.email, nombre=u.nombre, apellido=u.apellido,
        rol_id=str(u.rol_id), ver_solo_propios=False, es_asesor=bool(u.es_asesor),
    )


def _sembrar_aeropuertos(db: Session) -> None:
    nuevos = 0
    for iata, nombre, ciudad, pais in AEROPUERTOS:
        if db.query(OpeAeropuerto).filter(OpeAeropuerto.codigo_iata == iata).first():
            continue
        db.add(OpeAeropuerto(
            codigo_iata=iata, nombre=nombre, ciudad=ciudad, pais=pais,
            modalidad="AEREA", activo=True,
        ))
        nuevos += 1
    db.commit()
    if nuevos:
        print(f"Aeropuertos agregados al catálogo: {nuevos}")


def _sembrar_terceros(db: Session, actor_id: uuid.UUID) -> None:
    asesor = db.query(AdmUsuario).filter(AdmUsuario.es_asesor == True).first()

    for nit, razon, ciudad, depto in CLIENTES:
        if db.query(AdmTercero).filter(AdmTercero.nit == nit).first():
            continue
        db.add(AdmTercero(
            nit=nit,
            digito_verif=_digito_verificacion(nit),
            razon_social=razon,
            tipo_persona="JURIDICA",
            tipo_tercero="CLIENTE",
            regimen="ORDINARIO",
            responsable_iva=True,
            email=f"contacto@{razon.split()[0].lower()}.com.co",
            telefono="6015550100",
            direccion="Calle 100 # 15-20",
            ciudad=ciudad,
            departamento=depto,
            pais="Colombia",
            notas=f"{MARCA_DEMO} cliente de demostración",
            asesor_id=asesor.id if asesor else None,
            creado_por=actor_id,
        ))

    for nit, razon, ciudad, pais in CONTRAPARTES:
        if db.query(AdmTercero).filter(AdmTercero.nit == nit).first():
            continue
        db.add(AdmTercero(
            nit=nit,
            razon_social=razon,
            tipo_persona="JURIDICA",
            tipo_tercero="OTRO",
            responsable_iva=False,
            ciudad=ciudad,
            pais=pais,
            notas=f"{MARCA_DEMO} contraparte del exterior",
            creado_por=actor_id,
        ))

    db.commit()


def _lineas(db: Session, peso_kg: int) -> list[OpeCotizacionLineaCreate]:
    lineas: list[OpeCotizacionLineaCreate] = []
    orden = 1
    for nombre, venta, costo in PLANTILLA_LINEAS:
        c = db.query(OpeConcepto).filter(
            OpeConcepto.nombre == nombre, OpeConcepto.activo == True
        ).first()
        if not c:
            continue
        base = Decimal(str(peso_kg)) if c.tipo_calculo == "POR_KG" else Decimal("1")
        lineas.append(OpeCotizacionLineaCreate(
            seccion=c.seccion,
            orden=orden,
            concepto_id=c.id,
            descripcion=nombre,
            tipo_calculo=c.tipo_calculo,
            valor_unitario=venta,
            costo_unitario=costo,
            base=base,
            moneda=c.moneda,
        ))
        orden += 1
    return lineas


def _carpeta(
    db: Session, actor: UsuarioActual, operacion_id: uuid.UUID, spec: tuple,
    num_hawbs: int, con_manifiesto: bool, apertura: date, cerrada: bool,
    consecutivo_hawb: int,
) -> int:
    """Crea MAWB + HAWBs + manifiesto de una operación. Devuelve el consecutivo."""
    (idx, tipo, origen, destino, piezas, peso, cif, iata, _estado, _dias) = spec
    if num_hawbs == 0:
        return consecutivo_hawb

    aerolinea = db.query(OpeAerolinea).filter(OpeAerolinea.codigo_iata == iata).first()
    apt_org = db.query(OpeAeropuerto).filter(
        OpeAeropuerto.codigo_iata == CIUDADES[origen][0]).first()
    apt_dst = db.query(OpeAeropuerto).filter(
        OpeAeropuerto.codigo_iata == CIUDADES[destino][0]).first()

    cliente = db.query(AdmTercero).filter(AdmTercero.nit == CLIENTES[idx][0]).first()
    ext_nit = CIUDADES[origen][1] if tipo == "IMPORTACION" else CIUDADES[destino][1]
    externo = db.query(AdmTercero).filter(AdmTercero.nit == ext_nit).first()
    if tipo == "IMPORTACION":
        shipper, consignee = externo, cliente
    else:
        shipper, consignee = cliente, externo

    vuelo = f"{iata}{700 + (consecutivo_hawb % 90)}"
    fecha_vuelo = apertura + timedelta(days=3)
    trm = TRM_BASE + Decimal(str(consecutivo_hawb % 9 * 11))
    mercancia = MERCANCIAS[consecutivo_hawb % len(MERCANCIAS)]
    emitida = cerrada or num_hawbs > 1

    mawb = ops_svc.crear_mawb(db, operacion_id, OpeMawbCreate(
        prefix=PREFIJO_MAWB.get(iata),
        numero_mawb=f"{45000000 + consecutivo_hawb * 17:08d}",
        consignee_id=consignee.id if consignee else None,
        aerolinea_id=aerolinea.id if aerolinea else None,
        aeropuerto_origen_id=apt_org.id if apt_org else None,
        aeropuerto_destino_id=apt_dst.id if apt_dst else None,
        vuelo=vuelo,
        fecha_vuelo=fecha_vuelo,
        trm=trm,
        tipo_pago_flete="PPD",
        moneda_flete="USD",
        clase_tarifa="Q",
        piezas=piezas,
        peso_bruto_kg=Decimal(str(peso)),
        peso_cargable_kg=Decimal(str(peso)),
        tarifa_por_kg=Decimal("2.10"),
        descripcion_mercancia=mercancia,
        flete_total=(Decimal(str(peso)) * Decimal("2.10")).quantize(Decimal("0.01")),
        fsc=Decimal("0.35") * Decimal(str(peso)),
        fecha_ejecucion=apertura + timedelta(days=1),
        lugar_ejecucion="BOGOTA",
    ), actor)
    if emitida:
        ops_svc.actualizar_mawb(db, operacion_id, mawb.id, OpeMawbUpdate(estado="EMITIDA"), actor)

    hawbs = []
    piezas_resto, peso_resto = piezas, Decimal(str(peso))
    for i in range(num_hawbs):
        ultimo = i == num_hawbs - 1
        p_i = piezas_resto if ultimo else max(1, piezas // num_hawbs)
        k_i = peso_resto if ultimo else (Decimal(str(peso)) / num_hawbs).quantize(Decimal("0.01"))
        piezas_resto -= p_i
        peso_resto -= k_i

        h = ops_svc.crear_hawb(db, operacion_id, OpeHawbCreate(
            numero_hawb=f"UCC-26{consecutivo_hawb:04d}",
            mawb_id=mawb.id,
            shipper_id=shipper.id,
            consignee_id=consignee.id,
            aeropuerto_origen_id=apt_org.id if apt_org else None,
            aeropuerto_destino_id=apt_dst.id if apt_dst else None,
            aerolinea_id=aerolinea.id if aerolinea else None,
            vuelo=vuelo,
            fecha_vuelo=fecha_vuelo,
            trm=trm,
            tipo_pago_flete="PPD",
            moneda="USD",
            clase_tarifa="Q",
            piezas=p_i,
            peso_bruto_kg=k_i,
            peso_cargable_kg=k_i,
            tarifa="2.80",
            total_carga=str((k_i * Decimal("2.80")).quantize(Decimal("0.01"))),
            descripcion_mercancia=mercancia,
            fecha_ejecucion=apertura + timedelta(days=1),
            lugar_ejecucion="BOGOTA",
        ), actor)
        if emitida:
            ops_svc.actualizar_hawb(db, operacion_id, h.id, OpeHawbUpdate(estado="EMITIDA"), actor)
        hawbs.append((h, p_i, k_i))
        consecutivo_hawb += 1

    if con_manifiesto:
        man = ops_svc.crear_manifiesto(db, operacion_id, OpeManifiestoCreate(
            mawb_id=mawb.id,
            aerolinea_id=aerolinea.id if aerolinea else None,
            fecha=fecha_vuelo,
            lineas=[
                OpeManifiestoLineaCreate(
                    hawb_id=h.id,
                    exportador_id=shipper.id,
                    importador_id=consignee.id,
                    piezas=p_i,
                    peso_kg=k_i,
                    descripcion=mercancia,
                )
                for h, p_i, k_i in hawbs
            ],
        ), actor)
        if emitida:
            man.estado = "EMITIDA"
            db.add(man)
            db.commit()

    return consecutivo_hawb


def sembrar() -> None:
    db = SessionLocal()
    try:
        ya = db.query(OpeCotizacion).filter(OpeCotizacion.notas.like(f"%{MARCA_DEMO}%")).count()
        if ya:
            print(f"Ya existen {ya} cotizaciones demo. Ejecuta --limpiar primero si quieres regenerarlas.")
            return

        actor = _actor(db)
        actor_id = uuid.UUID(actor.id)
        print(f"Sembrando como {actor.nombre} {actor.apellido} <{actor.email}>")

        _sembrar_aeropuertos(db)
        _sembrar_terceros(db, actor_id)
        clientes = [
            db.query(AdmTercero).filter(AdmTercero.nit == nit).first()
            for nit, *_ in CLIENTES
        ]
        print(f"Terceros demo listos: {len(CLIENTES)} clientes, {len(CONTRAPARTES)} contrapartes")

        aerolineas = {a.codigo_iata: a.id for a in db.query(OpeAerolinea).all()}
        hoy = date.today()
        aprobadas: list[tuple[uuid.UUID, tuple]] = []

        for spec in COTIZACIONES:
            (idx, tipo, origen, destino, piezas, peso, cif, iata, estado, dias) = spec
            fecha = hoy - timedelta(days=dias)

            cot = svc.crear_cotizacion(db, OpeCotizacionCreate(
                cliente_id=clientes[idx].id,
                fecha=fecha,
                fecha_vigencia=hoy + timedelta(days=20),  # se retrocede más abajo
                tipo_operacion=tipo,
                modalidad="AEREA",
                origen=origen,
                destino=destino,
                aerolinea_id=aerolineas.get(iata),
                incoterm="CIF" if tipo == "IMPORTACION" else "FOB",
                piezas=piezas,
                peso_kg=Decimal(str(peso)),
                valor_mercancia=Decimal(str(cif)),
                moneda_mercancia="USD",
                valor_cif=Decimal(str(cif)),
                trm=TRM_BASE + Decimal(str(dias % 7 * 12)),
                notas=f"{MARCA_DEMO} Cotización de demostración. Precios sujetos a confirmación de espacio.",
                lineas=_lineas(db, peso),
            ), actor)

            if estado != "BORRADOR":
                svc.enviar_cotizacion(db, cot.id, actor)
            if estado == "APROBADA":
                aprobadas.append((cot.id, spec))
            elif estado == "RECHAZADA":
                svc.rechazar_cotizacion(db, cot.id, actor)

            # Vigencia real. Solo se puede retroceder cuando la cotización ya
            # salió de BORRADOR/ENVIADA, que son los únicos estados que
            # _marcar_vencidas toca. Las APROBADA siguen en ENVIADA aquí — se
            # aprueban en el bucle siguiente — así que su vigencia se retrocede
            # allá, ya aprobadas. VENCIDA se deja pasada a propósito.
            if estado == "RECHAZADA":
                cot.fecha_vigencia = fecha + timedelta(days=30)
            elif estado == "VENCIDA":
                cot.fecha_vigencia = fecha + timedelta(days=15)
            db.add(cot)
            db.commit()

        print(f"Cotizaciones creadas: {len(COTIZACIONES)}")

        consecutivo_hawb = 1
        for (cot_id, spec), (estado_op, dias, num_hawbs, con_man) in zip(aprobadas, OPERACIONES):
            op = svc.aprobar_cotizacion(db, cot_id, actor)
            apertura = hoy - timedelta(days=dias)

            # Ya está APROBADA: inmune a _marcar_vencidas, se puede retroceder.
            cot = db.get(OpeCotizacion, cot_id)
            cot.fecha_vigencia = cot.fecha + timedelta(days=30)
            db.add(cot)

            # La carpeta se crea antes de fijar el estado: los services rechazan
            # documentos sobre una operación CERRADA.
            consecutivo_hawb = _carpeta(
                db, actor, op.id, spec, num_hawbs, con_man,
                apertura, estado_op == "CERRADA", consecutivo_hawb,
            )

            op.fecha_apertura = apertura
            op.estado = estado_op
            db.add(op)
            db.commit()

        print(f"Operaciones creadas: {len(aprobadas)}")

        # Fuerza el marcado de vencidas para que el resumen refleje el estado real.
        svc.listar_cotizaciones(db, actor)
        _resumen(db)
    finally:
        db.close()


def limpiar() -> None:
    db = SessionLocal()
    try:
        cots = db.query(OpeCotizacion).filter(
            OpeCotizacion.notas.like(f"%{MARCA_DEMO}%")
        ).all()
        ids = [c.id for c in cots]
        if not ids:
            print("No hay cotizaciones demo que limpiar.")
        else:
            op_ids = [
                o.id for o in
                db.query(OpeOperacion).join(OpeCotizacion, OpeCotizacion.operacion_id == OpeOperacion.id)
                .filter(OpeCotizacion.id.in_(ids)).all()
            ]
            if op_ids:
                man_ids = [
                    m.id for m in
                    db.query(OpeManifiesto).filter(OpeManifiesto.operacion_id.in_(op_ids)).all()
                ]
                if man_ids:
                    db.query(OpeManifiestoLinea).filter(
                        OpeManifiestoLinea.manifiesto_id.in_(man_ids)
                    ).delete(synchronize_session=False)
                    db.query(OpeManifiesto).filter(
                        OpeManifiesto.id.in_(man_ids)
                    ).delete(synchronize_session=False)
                db.query(OpeHawb).filter(
                    OpeHawb.operacion_id.in_(op_ids)
                ).delete(synchronize_session=False)
                db.query(OpeMawb).filter(
                    OpeMawb.operacion_id.in_(op_ids)
                ).delete(synchronize_session=False)
                db.query(OpeOperacion).filter(
                    OpeOperacion.id.in_(op_ids)
                ).delete(synchronize_session=False)
            db.query(OpeCotizacionLinea).filter(
                OpeCotizacionLinea.cotizacion_id.in_(ids)
            ).delete(synchronize_session=False)
            db.query(OpeCotizacion).filter(
                OpeCotizacion.id.in_(ids)
            ).delete(synchronize_session=False)
            db.commit()
            print(f"Eliminadas {len(ids)} cotizaciones demo y {len(op_ids)} operaciones con su carpeta.")

        nits = [c[0] for c in CLIENTES] + [c[0] for c in CONTRAPARTES]
        borrados = db.query(AdmTercero).filter(
            AdmTercero.nit.in_(nits), AdmTercero.notas.like(f"%{MARCA_DEMO}%")
        ).delete(synchronize_session=False)
        db.commit()
        print(f"Eliminados {borrados} terceros demo. (Los aeropuertos del catálogo se conservan.)")
    finally:
        db.close()


def _resumen(db: Session) -> None:
    print("\nEstado final:")
    for estado in ("BORRADOR", "ENVIADA", "APROBADA", "RECHAZADA", "VENCIDA"):
        n = db.query(OpeCotizacion).filter(OpeCotizacion.estado == estado).count()
        print(f"  cotización {estado:<10} {n}")
    for estado in ("ABIERTA", "EN_CURSO", "CERRADA", "CANCELADA"):
        n = db.query(OpeOperacion).filter(OpeOperacion.estado == estado).count()
        print(f"  operación  {estado:<10} {n}")
    print(f"  MAWB       {db.query(OpeMawb).count()}")
    print(f"  HAWB       {db.query(OpeHawb).count()}")
    print(f"  manifiesto {db.query(OpeManifiesto).count()}")


if __name__ == "__main__":
    if "--limpiar" in sys.argv:
        limpiar()
    else:
        sembrar()
