"""
Asigna cuentas contables a los 4 tipos de producto.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_tipos_producto
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.contabilidad import CntCuenta
from app.models.inventario import InvTipoProducto

TIPOS = {
    "MERCANCIA": {
        "cuenta_inventario":        "143001",  # Mercancías para la venta
        "cuenta_costo_ventas":      "611010",  # Compras de mercancías
        "cuenta_ingreso":           "411005",  # Ventas brutas
        "cuenta_devolucion_venta":  "411010",  # Devoluciones en ventas
        "cuenta_devolucion_compra": "611015",  # Devoluciones en compras
        "cuenta_ajuste_entrada":    "143001",  # Mercancías para la venta
        "cuenta_ajuste_salida":     "611010",  # Compras de mercancías
    },
    "SERVICIO": {
        "cuenta_inventario":        None,
        "cuenta_costo_ventas":      None,
        "cuenta_ingreso":           "418005",  # Servicios prestados
        "cuenta_devolucion_venta":  "411010",  # Devoluciones en ventas
        "cuenta_devolucion_compra": None,
        "cuenta_ajuste_entrada":    None,
        "cuenta_ajuste_salida":     None,
    },
    "MATERIA_PRIMA": {
        "cuenta_inventario":        "140501",  # Materias primas
        "cuenta_costo_ventas":      "710505",  # Materias primas consumidas
        "cuenta_ingreso":           "411005",  # Ventas brutas
        "cuenta_devolucion_venta":  "411010",  # Devoluciones en ventas
        "cuenta_devolucion_compra": "611015",  # Devoluciones en compras
        "cuenta_ajuste_entrada":    "140501",  # Materias primas
        "cuenta_ajuste_salida":     "710505",  # Materias primas consumidas
    },
    "INSUMO": {
        "cuenta_inventario":        "143001",  # Mercancías para la venta
        "cuenta_costo_ventas":      "711005",  # Materiales indirectos
        "cuenta_ingreso":           "418005",  # Servicios prestados
        "cuenta_devolucion_venta":  "411010",  # Devoluciones en ventas
        "cuenta_devolucion_compra": "611015",  # Devoluciones en compras
        "cuenta_ajuste_entrada":    "143001",  # Mercancías para la venta
        "cuenta_ajuste_salida":     "711005",  # Materiales indirectos
    },
}


def run():
    db = SessionLocal()
    try:
        cuentas = {c.codigo: c.id for c in db.query(CntCuenta).all()}

        def cid(codigo):
            if not codigo:
                return None
            c = cuentas.get(codigo)
            if not c:
                print(f"  [!] Cuenta {codigo} no encontrada")
            return c

        actualizados = 0
        for codigo, campos in TIPOS.items():
            tipo = db.query(InvTipoProducto).filter(InvTipoProducto.codigo == codigo).first()
            if not tipo:
                print(f"  [!] Tipo {codigo} no encontrado")
                continue
            tipo.cuenta_inventario_id        = cid(campos["cuenta_inventario"])
            tipo.cuenta_costo_ventas_id      = cid(campos["cuenta_costo_ventas"])
            tipo.cuenta_ingreso_id           = cid(campos["cuenta_ingreso"])
            tipo.cuenta_devolucion_venta_id  = cid(campos["cuenta_devolucion_venta"])
            tipo.cuenta_devolucion_compra_id = cid(campos["cuenta_devolucion_compra"])
            tipo.cuenta_ajuste_entrada_id    = cid(campos["cuenta_ajuste_entrada"])
            tipo.cuenta_ajuste_salida_id     = cid(campos["cuenta_ajuste_salida"])
            print(f"  [+] {codigo} — cuentas asignadas")
            actualizados += 1

        db.commit()
        print(f"\nTipos actualizados: {actualizados}")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
