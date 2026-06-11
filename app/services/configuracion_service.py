from datetime import datetime, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.admin import AdmConfiguracion
from app.schemas.auth import UsuarioActual
from app.schemas.configuracion import ConfiguracionUpdate, ConfiguracionResponse


def listar(db: Session) -> list[ConfiguracionResponse]:
    return db.query(AdmConfiguracion).order_by(AdmConfiguracion.clave).all()


def actualizar(db: Session, clave: str, data: ConfiguracionUpdate, actor: UsuarioActual) -> ConfiguracionResponse:
    obj = db.query(AdmConfiguracion).filter(AdmConfiguracion.clave == clave).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Clave de configuración no encontrada")

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
