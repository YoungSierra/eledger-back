"""
Siembra 10 conceptos de causación CxP con IVA y retenciones.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_conceptos_cxp
"""
import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.admin import AdmConcepto, AdmConceptoCuenta, AdmConceptoRetencion, AdmTarifaIva, AdmRetencion
from app.models.contabilidad import CntCuenta

SUPERADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_iva(db, nombre):
    r = db.query(AdmTarifaIva).filter(AdmTarifaIva.nombre == nombre).first()
    if not r:
        raise ValueError(f"Tarifa IVA no encontrada: {nombre}")
    return r.id


def get_ret(db, nombre_like):
    r = db.query(AdmRetencion).filter(AdmRetencion.nombre.ilike(f"%{nombre_like}%")).first()
    if not r:
        raise ValueError(f"Retención no encontrada: {nombre_like}")
    return r.id


def get_cuenta(db, codigo):
    r = db.query(CntCuenta).filter(CntCuenta.codigo == codigo).first()
    if not r:
        raise ValueError(f"Cuenta no encontrada: {codigo}")
    return r.id


def run():
    db = SessionLocal()
    try:
        # IDs IVA
        iva_19    = get_iva(db, "IVA 19%")
        iva_exento = get_iva(db, "Exento")
        iva_excluido = get_iva(db, "Excluido")

        # IDs retenciones
        ret_hon_pn   = get_ret(db, "honorarios personas naturales")
        ret_hon_pj   = get_ret(db, "honorarios personas jur")
        ret_arri     = get_ret(db, "arrendamiento inmuebles")
        ret_serv     = get_ret(db, "servicios generales")
        ret_compras  = get_ret(db, "compras generales")
        ret_transp   = get_ret(db, "transporte de carga")
        ret_ica_serv = get_ret(db, "ReteICA servicios")
        ret_iva      = get_ret(db, "ReteIVA 15%")

        # IDs cuentas
        c_hon_pn     = get_cuenta(db, "511005")
        c_hon_pj     = get_cuenta(db, "511010")
        c_arri       = get_cuenta(db, "512005")
        c_energia    = get_cuenta(db, "513505")
        c_internet   = get_cuenta(db, "513520")
        c_transp     = get_cuenta(db, "513535")
        c_aseo       = get_cuenta(db, "513530")
        c_mant_comp  = get_cuenta(db, "514515")
        c_software   = get_cuenta(db, "513540")
        c_servicios  = get_cuenta(db, "5135")

        CONCEPTOS = [
            {
                "codigo": "HON-PN",
                "nombre": "Honorarios — Persona natural",
                "descripcion": "Servicios profesionales prestados por personas naturales",
                "tarifa_iva": iva_19,
                "cuenta": c_hon_pn,
                "retenciones": [ret_hon_pn, ret_ica_serv, ret_iva],
            },
            {
                "codigo": "HON-PJ",
                "nombre": "Honorarios — Persona jurídica",
                "descripcion": "Servicios profesionales prestados por personas jurídicas",
                "tarifa_iva": iva_19,
                "cuenta": c_hon_pj,
                "retenciones": [ret_hon_pj, ret_ica_serv],
            },
            {
                "codigo": "ARRI-INM",
                "nombre": "Arrendamiento de inmueble",
                "descripcion": "Canon de arrendamiento de oficinas, bodegas o locales",
                "tarifa_iva": iva_exento,
                "cuenta": c_arri,
                "retenciones": [ret_arri, ret_ica_serv],
            },
            {
                "codigo": "SERV-GEN",
                "nombre": "Servicios generales",
                "descripcion": "Prestación de servicios sin categoría específica",
                "tarifa_iva": iva_19,
                "cuenta": c_servicios,
                "retenciones": [ret_serv, ret_ica_serv],
            },
            {
                "codigo": "ENERGIA",
                "nombre": "Energía eléctrica",
                "descripcion": "Factura de servicio de energía eléctrica",
                "tarifa_iva": iva_19,
                "cuenta": c_energia,
                "retenciones": [],
            },
            {
                "codigo": "INTERNET",
                "nombre": "Internet y datos",
                "descripcion": "Servicio de conectividad, internet y telecomunicaciones",
                "tarifa_iva": iva_19,
                "cuenta": c_internet,
                "retenciones": [ret_serv],
            },
            {
                "codigo": "TRANSP-CG",
                "nombre": "Transporte de carga",
                "descripcion": "Fletes y transporte terrestre de mercancía",
                "tarifa_iva": iva_excluido,
                "cuenta": c_transp,
                "retenciones": [ret_transp, ret_ica_serv],
            },
            {
                "codigo": "ASEO-VIG",
                "nombre": "Aseo y vigilancia",
                "descripcion": "Servicios de limpieza, aseo y seguridad física",
                "tarifa_iva": iva_19,
                "cuenta": c_aseo,
                "retenciones": [ret_serv, ret_ica_serv],
            },
            {
                "codigo": "MANT-COMP",
                "nombre": "Mantenimiento equipo de cómputo",
                "descripcion": "Soporte técnico y mantenimiento de hardware y software",
                "tarifa_iva": iva_19,
                "cuenta": c_mant_comp,
                "retenciones": [ret_serv, ret_ica_serv],
            },
            {
                "codigo": "SOFTWARE",
                "nombre": "Servicios de software (SaaS)",
                "descripcion": "Licencias, suscripciones y plataformas digitales",
                "tarifa_iva": iva_19,
                "cuenta": c_software,
                "retenciones": [ret_serv, ret_ica_serv],
            },
        ]

        creados = 0
        for d in CONCEPTOS:
            existe = db.query(AdmConcepto).filter(AdmConcepto.codigo == d["codigo"]).first()
            if existe:
                print(f"  [skip] {d['codigo']} ya existe")
                continue

            obj = AdmConcepto(
                codigo=d["codigo"], nombre=d["nombre"], modulo="cxp",
                descripcion=d["descripcion"], tarifa_iva_id=d["tarifa_iva"],
                activo=True, creado_por=SUPERADMIN_ID,
            )
            db.add(obj); db.flush()

            db.add(AdmConceptoCuenta(
                concepto_id=obj.id, cuenta_id=d["cuenta"],
                tipo_movimiento="DEBITO", activo=True,
            ))

            for ret_id in d["retenciones"]:
                db.add(AdmConceptoRetencion(
                    concepto_id=obj.id, retencion_id=ret_id, activo=True,
                ))

            print(f"  [ok] {d['codigo']} — {d['nombre']}")
            creados += 1

        db.commit()
        print(f"\nConceptos creados: {creados}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
