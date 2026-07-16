"""
Siembra los valores iniciales de adm_configuracion.

Uso:
    cd backend
    venv\\Scripts\\python -m app.core.seed_configuracion
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.admin import AdmConfiguracion

CONFIGS = [
    # Contabilidad
    ("permitir_correccion_asientos",    "true",    "boolean", "Permite generar contraasientos automáticos para corregir asientos publicados"),
    ("periodo_cierre_automatico",       "false",   "boolean", "Cierra automáticamente los períodos al iniciar uno nuevo"),

    # CxC
    ("dias_alerta_vencimiento_cxc",     "5",       "integer", "Días antes del vencimiento de una factura CxC para mostrar alerta"),
    ("dias_alerta_vencimiento_cxp",     "5",       "integer", "Días antes del vencimiento de una factura CxP para mostrar alerta"),

    # Inventario
    ("metodo_valoracion_inventario",    "PROMEDIO","string",  "Método de valoración de inventario: PROMEDIO o PEPS"),
    ("permite_stock_negativo",          "false",   "boolean", "Permite generar movimientos de salida cuando el stock es insuficiente"),

    # Facturación
    ("dias_validez_cotizacion",         "30",      "integer", "Días de validez por defecto para una cotización de venta"),
    ("factura_requiere_cotizacion",     "false",   "boolean", "Exige que toda factura de venta tenga una cotización aprobada previa"),

]


def run():
    db = SessionLocal()
    try:
        creadas = 0
        for clave, valor, tipo, descripcion in CONFIGS:
            existe = db.query(AdmConfiguracion).filter(AdmConfiguracion.clave == clave).first()
            if not existe:
                db.add(AdmConfiguracion(clave=clave, valor=valor, tipo=tipo, descripcion=descripcion))
                print(f"  [+] {clave} = {valor}")
                creadas += 1
            else:
                print(f"  [=] {clave} ya existe")
        db.commit()
        print(f"\nConfiguración sembrada: {creadas} claves nuevas")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
