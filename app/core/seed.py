"""
Script de seed inicial.
Crea el rol superadmin, los módulos del sistema y el primer usuario administrador.
Solo se ejecuta si no existen usuarios en la BD.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed
"""
import sys
import uuid

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.admin import (
    AdmModulo, AdmRol, AdmUsuario,
    AdmTipoDocumento, AdmConsecutivo, AdmMoneda,
)

SYSTEM_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

MODULOS = [
    ("administracion", "Administración", 1),
    ("contabilidad",   "Contabilidad",   2),
    ("cxc",            "Cuentas por Cobrar", 3),
    ("cxp",            "Cuentas por Pagar",  4),
    ("inventario",     "Inventario",      5),
    ("compras",        "Compras",         6),
    ("facturacion",    "Facturación",     7),
    ("bancos",         "Bancos",          8),
    ("reportes",       "Reportes",        9),
]

TIPOS_DOCUMENTO = [
    ("FAC",  "Factura de venta",           "facturacion"),
    ("NCC",  "Nota crédito cliente",       "facturacion"),
    ("NDB",  "Nota débito cliente",        "facturacion"),
    ("REC",  "Recibo de caja",             "cxc"),
    ("OC",   "Orden de compra",            "compras"),
    ("FCP",  "Factura compra proveedor",   "cxp"),
    ("CP",   "Comprobante de pago",        "cxp"),
    ("AM",   "Asiento contable manual",    "contabilidad"),
    ("DEP",  "Depreciación",              "contabilidad"),
    ("NOM",  "Nómina",                   "contabilidad"),
    ("ANU",  "Anulación contable",        "contabilidad"),
    ("AJU",  "Ajuste contable",           "contabilidad"),
    ("REM",  "Remisión / despacho",        "facturacion"),
    ("RECP", "Recepción de mercancía",       "compras"),
    ("COT",  "Cotización de venta",        "facturacion"),
    ("ANT",  "Anticipo de cliente",        "cxc"),
    ("ANTP", "Anticipo a proveedor",       "cxp"),
]


def run(email: str, password: str, nombre: str, apellido: str):
    db: Session = SessionLocal()
    try:
        if db.query(AdmUsuario).count() > 0:
            print("Ya existen usuarios. Seed omitido.")
            return

        print("Creando módulos...")
        modulos = {}
        for codigo, nombre_mod, orden in MODULOS:
            m = AdmModulo(codigo=codigo, nombre=nombre_mod, orden=orden)
            db.add(m)
            modulos[codigo] = m
        db.flush()

        print("Creando rol superadmin...")
        rol = AdmRol(nombre="superadmin", descripcion="Acceso total al sistema", creado_por=SYSTEM_UUID)
        db.add(rol)
        db.flush()

        print(f"Creando usuario administrador: {email}")
        usuario = AdmUsuario(
            email=email,
            nombre=nombre,
            apellido=apellido,
            password_hash=hash_password(password),
            rol_id=rol.id,
            creado_por=SYSTEM_UUID,
        )
        db.add(usuario)
        db.flush()

        print("Creando moneda base (COP)...")
        cop = AdmMoneda(
            codigo="COP",
            nombre="Peso colombiano",
            simbolo="$",
            decimales=2,
            es_funcional=True,
            creado_por=usuario.id,
        )
        db.add(cop)

        print("Creando tipos de documento y consecutivos...")
        for codigo, nombre_doc, modulo in TIPOS_DOCUMENTO:
            td = AdmTipoDocumento(codigo=codigo, nombre=nombre_doc, modulo=modulo)
            db.add(td)
            db.flush()
            consec = AdmConsecutivo(
                tipo_documento_id=td.id,
                prefijo=codigo,
                numero_actual=0,
                numero_inicio=1,
                longitud_minima=5,
            )
            db.add(consec)

        db.commit()
        print("\nSeed completado exitosamente.")
        print(f"  Usuario: {email}")
        print(f"  Rol:     superadmin")
        print(f"  Módulos: {len(MODULOS)}")
        print(f"  Tipos de documento: {len(TIPOS_DOCUMENTO)}")

    except Exception as e:
        db.rollback()
        print(f"Error en seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run(
        email="admin@eledger.com",
        password="Admin123!",
        nombre="Administrador",
        apellido="Sistema",
    )
