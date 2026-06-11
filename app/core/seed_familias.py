"""
Siembra 5 familias de productos con cuentas contables asignadas.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_familias
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import uuid
from app.core.database import SessionLocal
from app.models.admin import AdmUsuario
from app.models.contabilidad import CntCuenta
from app.models.inventario import InvFamilia

FAMILIAS = [
    {
        "codigo": "MERC",
        "nombre": "Mercancías para la venta",
        "descripcion": "Productos terminados destinados a la comercialización",
        "cuenta_inventario":        "143001",
        "cuenta_costo_ventas":      "611010",
        "cuenta_ingreso":           "411005",
        "cuenta_devolucion_venta":  "411010",
        "cuenta_devolucion_compra": "611015",
        "cuenta_ajuste_entrada":    "143001",
        "cuenta_ajuste_salida":     "611010",
    },
    {
        "codigo": "MPRIMA",
        "nombre": "Materias primas",
        "descripcion": "Insumos base para procesos de transformación o manufactura",
        "cuenta_inventario":        "140501",
        "cuenta_costo_ventas":      "710505",
        "cuenta_ingreso":           "411005",
        "cuenta_devolucion_venta":  "411010",
        "cuenta_devolucion_compra": "611015",
        "cuenta_ajuste_entrada":    "140501",
        "cuenta_ajuste_salida":     "710505",
    },
    {
        "codigo": "PRODTERM",
        "nombre": "Productos terminados",
        "descripcion": "Artículos listos para la venta resultado de proceso productivo",
        "cuenta_inventario":        "142001",
        "cuenta_costo_ventas":      "611010",
        "cuenta_ingreso":           "411005",
        "cuenta_devolucion_venta":  "411010",
        "cuenta_devolucion_compra": "611015",
        "cuenta_ajuste_entrada":    "142001",
        "cuenta_ajuste_salida":     "611010",
    },
    {
        "codigo": "INSUMOS",
        "nombre": "Insumos y suministros",
        "descripcion": "Materiales de consumo interno: papelería, aseo, embalajes",
        "cuenta_inventario":        "143001",
        "cuenta_costo_ventas":      "711005",
        "cuenta_ingreso":           "418005",
        "cuenta_devolucion_venta":  "411010",
        "cuenta_devolucion_compra": "611015",
        "cuenta_ajuste_entrada":    "143001",
        "cuenta_ajuste_salida":     "711005",
    },
    {
        "codigo": "SERV",
        "nombre": "Servicios",
        "descripcion": "Servicios prestados sin manejo de inventario físico",
        "cuenta_inventario":        None,
        "cuenta_costo_ventas":      None,
        "cuenta_ingreso":           "418005",
        "cuenta_devolucion_venta":  "411010",
        "cuenta_devolucion_compra": None,
        "cuenta_ajuste_entrada":    None,
        "cuenta_ajuste_salida":     None,
    },
]


def run():
    db = SessionLocal()
    try:
        # Obtener superadmin como creado_por
        admin = db.query(AdmUsuario).filter(AdmUsuario.activo == True).first()
        if not admin:
            print("No hay usuarios activos. Abortando.")
            return

        # Índice de cuentas por código
        cuentas = {c.codigo: c.id for c in db.query(CntCuenta).all()}

        def cuenta_id(codigo):
            if not codigo:
                return None
            cid = cuentas.get(codigo)
            if not cid:
                print(f"  [!] Cuenta {codigo} no encontrada")
            return cid

        creadas = 0
        for f in FAMILIAS:
            existe = db.query(InvFamilia).filter(InvFamilia.codigo == f["codigo"]).first()
            if existe:
                print(f"  [=] {f['codigo']} ya existe, omitiendo")
                continue
            db.add(InvFamilia(
                id=uuid.uuid4(),
                codigo=f["codigo"],
                nombre=f["nombre"],
                descripcion=f["descripcion"],
                cuenta_inventario_id=cuenta_id(f["cuenta_inventario"]),
                cuenta_costo_ventas_id=cuenta_id(f["cuenta_costo_ventas"]),
                cuenta_ingreso_id=cuenta_id(f["cuenta_ingreso"]),
                cuenta_devolucion_venta_id=cuenta_id(f["cuenta_devolucion_venta"]),
                cuenta_devolucion_compra_id=cuenta_id(f["cuenta_devolucion_compra"]),
                cuenta_ajuste_entrada_id=cuenta_id(f["cuenta_ajuste_entrada"]),
                cuenta_ajuste_salida_id=cuenta_id(f["cuenta_ajuste_salida"]),
                activo=True,
                creado_por=admin.id,
            ))
            print(f"  [+] {f['codigo']} — {f['nombre']}")
            creadas += 1

        db.commit()
        print(f"\nFamilias creadas: {creadas}")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
