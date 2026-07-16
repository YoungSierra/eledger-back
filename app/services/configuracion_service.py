from datetime import datetime, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.admin import AdmConfiguracion
from app.models.inventario import InvMovimiento
from app.schemas.auth import UsuarioActual
from app.schemas.configuracion import ConfiguracionUpdate, ConfiguracionResponse


_MSG_METODO_VALORACION = (
    "No se puede cambiar el método de valoración: ya existen movimientos de inventario registrados."
)


def _motivo_bloqueo(db: Session, clave: str) -> str | None:
    """Devuelve el motivo por el que un parámetro no puede editarse, o None si es libre."""
    # El método de valoración de inventario es una política contable (principio de
    # uniformidad): no puede cambiarse una vez existe costeo calculado, o quedarían
    # inconsistentes los costos históricos ya registrados en el kardex.
    if clave == "metodo_valoracion_inventario" and db.query(InvMovimiento.id).first() is not None:
        return _MSG_METODO_VALORACION
    return None


def listar(db: Session) -> list[ConfiguracionResponse]:
    filas = db.query(AdmConfiguracion).order_by(AdmConfiguracion.clave).all()
    resp: list[ConfiguracionResponse] = []
    for obj in filas:
        r = ConfiguracionResponse.model_validate(obj)
        motivo = _motivo_bloqueo(db, obj.clave)
        r.bloqueado = motivo is not None
        r.motivo_bloqueo = motivo
        resp.append(r)
    return resp


def actualizar(db: Session, clave: str, data: ConfiguracionUpdate, actor: UsuarioActual) -> ConfiguracionResponse:
    obj = db.query(AdmConfiguracion).filter(AdmConfiguracion.clave == clave).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Clave de configuración no encontrada")

    if data.valor != obj.valor:
        motivo = _motivo_bloqueo(db, clave)
        if motivo is not None:
            raise HTTPException(status_code=409, detail=motivo)

    # Validar según tipo
    if obj.tipo == "boolean" and data.valor not in ("true", "false"):
        raise HTTPException(status_code=400, detail="Valor debe ser 'true' o 'false'")
    if obj.tipo == "integer":
        try:
            int(data.valor)
        except ValueError:
            raise HTTPException(status_code=400, detail="Valor debe ser un número entero")
    if obj.tipo == "numeric":
        try:
            float(data.valor)
        except ValueError:
            raise HTTPException(status_code=400, detail="Valor debe ser un número")

    obj.valor = data.valor
    obj.modificado_por = uuid.UUID(actor.id)
    obj.modificado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj
