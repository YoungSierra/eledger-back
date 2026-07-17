"""
Crea las tablas adm_opcion y adm_permiso_opcion si no existen,
y siembra las opciones del menú. Otorga acceso total al superadmin.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_opciones
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import Base, engine, SessionLocal
from app.models.admin import AdmModulo, AdmOpcion, AdmPermisoOpcion, AdmRol

# Estructura del menú: (modulo_codigo, opcion_codigo, nombre, ruta, orden, implementada)
OPCIONES = [
    ("administracion", "empresa",   "Empresa",            "/dashboard/empresa",              1, True),
    ("administracion", "usuarios",  "Usuarios",           "/dashboard/usuarios",             2, True),
    ("administracion", "periodos",  "Períodos contables", "/dashboard/periodos",             3, True),
    ("administracion", "roles",     "Roles y permisos",   "/dashboard/roles",                4, True),
    ("administracion", "trm",              "TRM histórica",        "/dashboard/administracion/trm",             5, True),
    ("contabilidad", "nomina_electronica", "Nómina electrónica", "/dashboard/contabilidad/nomina-electronica", 5, False),
    ("administracion", "monedas",           "Monedas",            "/dashboard/administracion/monedas",            7, True),
    ("administracion", "configuracion",     "Parámetros globales", "/dashboard/administracion/configuracion",       8, True),
    ("administracion", "parametros_cxc",   "Parámetros CxC",     "/dashboard/administracion/parametros-cxc",      9, True),

    ("contabilidad", "cuentas",        "Plan de cuentas",   "/dashboard/contabilidad/cuentas",       1, True),
    ("contabilidad", "centros_costo",  "Centros de costo",  "/dashboard/contabilidad/centros-costo", 2, True),
    ("contabilidad", "terceros",       "Terceros",          "/dashboard/contabilidad/terceros",      3, True),
    ("contabilidad", "asientos",       "Asientos",          "/dashboard/contabilidad/asientos",      4, True),

    ("cxc", "resumen_cxc",    "Resumen de cartera",  "/dashboard/cxc/resumen",      1, True),
    ("cxc", "documentos_cxc", "Documentos CxC",      "/dashboard/cxc/documentos",   2, True),
    ("cxc", "recibos",        "Recibos de caja",     "/dashboard/cxc/recibos",      3, True),
    ("cxc", "notas_cxc",      "Notas crédito",       "/dashboard/cxc/notas",        4, False),
    ("cxc", "notas_deb_cxc",  "Notas débito cliente","/dashboard/cxc/notas-debito", 5, False),
    ("cxc", "anticipos_cxc",  "Anticipos",           "/dashboard/cxc/anticipos",    6, False),

    ("cxp", "facturas_cxp",   "Facturas proveedor",     "/dashboard/cxp/facturas",     1, True),
    ("cxp", "comprobantes",   "Comprobantes de pago",   "/dashboard/cxp/comprobantes", 2, True),
    ("cxp", "notas_cxp",      "Notas crédito",          "/dashboard/cxp/notas",        3, False),
    ("cxp", "notas_deb_cxp",  "Notas débito proveedor", "/dashboard/cxp/notas-debito", 4, False),
    ("cxp", "anticipos_cxp",  "Anticipos proveedor",    "/dashboard/cxp/anticipos",    5, False),
    ("cxp", "conceptos_cxp",  "Conceptos de causación", "/dashboard/cxp/conceptos",    6, True),
    ("cxp", "saldos_cxp",     "Saldos proveedores",     "/dashboard/cxp/saldos",       7, True),
    ("administracion", "parametros_cxp", "Parámetros CxP", "/dashboard/administracion/parametros-cxp", 10, True),

    ("inventario", "saldos",       "Saldos / Kardex", "/dashboard/inventario/saldos",      1, True),
    ("inventario", "productos",    "Productos",       "/dashboard/inventario/productos",   2, True),
    ("inventario", "bodegas",      "Bodegas",         "/dashboard/inventario/bodegas",     3, True),
    ("inventario", "movimientos",  "Movimientos",     "/dashboard/inventario/movimientos", 4, True),
    ("inventario", "remisiones",   "Remisiones",      "/dashboard/inventario/remisiones",  5, False),

    ("compras", "ordenes",     "Órdenes de compra", "/dashboard/compras/ordenes",     1, True),
    ("compras", "recepciones", "Recepciones",       "/dashboard/compras/recepciones",  2, True),

    ("facturacion", "facturas_fac",  "Facturas de venta",    "/dashboard/facturacion/facturas",      1, True),
    ("facturacion", "cotizaciones",  "Cotizaciones",         "/dashboard/facturacion/cotizaciones",  2, False),
    ("facturacion", "devoluciones",  "Devoluciones",         "/dashboard/facturacion/devoluciones",  3, False),
    ("facturacion", "electronica",   "Factura electrónica",  "/dashboard/facturacion/electronica",   5, True),

    ("bancos", "bancos_cuentas",  "Cuentas bancarias",  "/dashboard/bancos/cuentas",         1, True),
    ("bancos", "extractos",      "Extractos",          "/dashboard/bancos/extractos",       2, False),
    ("bancos", "conciliacion",   "Conciliación",       "/dashboard/bancos/conciliacion",    3, False),
    ("bancos", "chequeras",      "Chequeras",          "/dashboard/bancos/chequeras",       4, True),
    ("bancos", "transferencias", "Transferencias",     "/dashboard/bancos/transferencias",  5, False),

    ("facturacion", "resoluciones", "Resoluciones DIAN", "/dashboard/facturacion/resoluciones", 6, True),

    ("operaciones", "cotizaciones",  "Cotizaciones",   "/dashboard/operaciones/cotizaciones", 1, True),
    ("operaciones", "operaciones",   "Operaciones",    "/dashboard/operaciones/operaciones",  2, True),
    ("operaciones", "aerolineas",    "Aerolíneas",     "/dashboard/operaciones/aerolineas",   3, True),
    ("operaciones", "aeropuertos",   "Aeropuertos",    "/dashboard/operaciones/aeropuertos",  4, True),
    ("operaciones", "conceptos",     "Conceptos",      "/dashboard/operaciones/conceptos",    5, True),

    ("reportes", "balance",         "Balance general",         "/dashboard/reportes/balance",       1, True),
    ("reportes", "resultados",      "Estado de resultados",    "/dashboard/reportes/resultados",    2, True),
    ("reportes", "flujo",           "Flujo de efectivo",       "/dashboard/reportes/flujo",         3, False),
    ("reportes", "patrimonio",      "Cambios en patrimonio",   "/dashboard/reportes/patrimonio",    4, False),
    ("reportes", "mayor",           "Libro mayor",             "/dashboard/reportes/mayor",         5, True),
    ("reportes", "balanza",         "Balanza de comprobación", "/dashboard/reportes/balanza",       6, True),
    ("reportes", "inv_valorado",    "Inventario valorado",     "/dashboard/reportes/inventario",    8, True),
    ("reportes", "auxiliar_tercero","Auxiliar por tercero",    "/dashboard/reportes/auxiliar",      9, True),
    ("reportes", "auxiliar_centro_costo","Auxiliar por centro de costo","/dashboard/reportes/auxiliar-centro-costo", 10, True),
    ("reportes", "concil_ban",      "Conciliación bancaria",   "/dashboard/reportes/conciliacion", 11, False),
    ("reportes", "ventas_agrup",    "Ventas por agrupación",   "/dashboard/reportes/ventas",       12, True),
    ("reportes", "compras_agrup",   "Compras por agrupación",  "/dashboard/reportes/compras",      13, True),
]


def run():
    # Crear tablas nuevas
    Base.metadata.create_all(engine, checkfirst=True)
    print("Tablas verificadas/creadas.")

    db = SessionLocal()
    try:
        # Cargar módulos
        modulos = {m.codigo: m for m in db.query(AdmModulo).all()}

        # Sembrar opciones
        creadas = 0
        for mod_codigo, op_codigo, nombre, ruta, orden, implementada in OPCIONES:
            modulo = modulos.get(mod_codigo)
            if not modulo:
                print(f"  [!] Módulo no encontrado: {mod_codigo}")
                continue
            existe = db.query(AdmOpcion).filter(
                AdmOpcion.modulo_id == modulo.id,
                AdmOpcion.codigo == op_codigo,
            ).first()
            if not existe:
                db.add(AdmOpcion(
                    modulo_id=modulo.id,
                    codigo=op_codigo,
                    nombre=nombre,
                    ruta=ruta,
                    orden=orden,
                    implementada=implementada,
                ))
                creadas += 1
            else:
                # Actualizar implementada si cambió
                if existe.implementada != implementada:
                    existe.implementada = implementada
        db.flush()
        print(f"Opciones creadas: {creadas}")

        # Dar acceso total al superadmin a todas las opciones
        superadmin = db.query(AdmRol).filter(AdmRol.nombre == "superadmin").first()
        if superadmin:
            todas = db.query(AdmOpcion).all()
            permisos_exist = {
                p.opcion_id
                for p in db.query(AdmPermisoOpcion).filter(AdmPermisoOpcion.rol_id == superadmin.id).all()
            }
            nuevos = 0
            for op in todas:
                if op.id not in permisos_exist:
                    db.add(AdmPermisoOpcion(
                        rol_id=superadmin.id, opcion_id=op.id,
                        puede_ver=True, puede_crear=True, puede_editar=True, puede_eliminar=True,
                    ))
                    nuevos += 1
            print(f"Permisos superadmin nuevos: {nuevos}")

        db.commit()
        print("Seed de opciones completado.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
