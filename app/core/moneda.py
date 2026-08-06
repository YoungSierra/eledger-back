"""Conversión a moneda funcional para reportes que agregan importes.

**Regla del proyecto:** todo lo que suma —libros, cartera, saldos por pagar—
se presenta en moneda funcional. Sumar dólares con pesos produce un número sin
significado, y es un error silencioso: nadie nota que el total está mal.

La valoración usa la **TRM del corte** y, si no hay tasa publicada para esa
moneda, la **TRM histórica del propio documento**.
"""
from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import Date, cast
from sqlalchemy.orm import Session

from app.models.admin import AdmMoneda, AdmTrm


def moneda_funcional(db: Session) -> AdmMoneda | None:
    return db.query(AdmMoneda).filter(AdmMoneda.es_funcional == True, AdmMoneda.activo == True).first()


def trm_corte(db: Session, fecha: date) -> dict[uuid.UUID, Decimal]:
    """TRM vigente a la fecha de corte, indexada por moneda de origen.

    Toma la última tasa publicada **en o antes** del corte, no la del día exacto:
    el corte puede caer en fin de semana o festivo y ahí no hay publicación.
    """
    func = moneda_funcional(db)
    if not func:
        return {}
    tasas: dict[uuid.UUID, Decimal] = {}
    for m in db.query(AdmMoneda).filter(AdmMoneda.activo == True, AdmMoneda.id != func.id).all():
        fila = (
            db.query(AdmTrm)
            .filter(AdmTrm.moneda_origen_id == m.id,
                    AdmTrm.moneda_destino_id == func.id,
                    cast(AdmTrm.fecha, Date) <= fecha)
            .order_by(AdmTrm.fecha.desc())
            .first()
        )
        if fila and fila.tasa:
            tasas[m.id] = Decimal(str(fila.tasa))
    return tasas


def a_funcional(doc, tasas: dict, moneda_func_id: uuid.UUID, valor: Decimal) -> Decimal:
    """Convierte un importe del documento a moneda funcional.

    `doc` solo necesita exponer `moneda_id` y `trm`, así que sirve igual para
    documentos de cartera y de cuentas por pagar.
    """
    if valor is None:
        return Decimal("0")
    if doc.moneda_id == moneda_func_id:
        return Decimal(valor)
    trm = tasas.get(doc.moneda_id) or doc.trm or Decimal("1")
    return (Decimal(valor) * trm).quantize(Decimal("0.01"))
