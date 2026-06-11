from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.configuracion import ConfiguracionUpdate, ConfiguracionResponse
from app.services import configuracion_service

router = APIRouter(prefix="/configuracion", tags=["Configuración"])


@router.get("", response_model=list[ConfiguracionResponse])
def listar(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return configuracion_service.listar(db)


@router.put("/{clave}", response_model=ConfiguracionResponse)
def actualizar(
    clave: str,
    body: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return configuracion_service.actualizar(db, clave, body, actor)
