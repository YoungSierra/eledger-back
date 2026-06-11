from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.parametros import (
    CxcParametroUpdate, CxcParametroResponse,
    CxpParametroUpdate, CxpParametroResponse,
)
from app.services import parametros_service

router_cxc = APIRouter(prefix="/parametros-cxc", tags=["Parametrización CxC"])
router_cxp = APIRouter(prefix="/parametros-cxp", tags=["Parametrización CxP"])


@router_cxc.get("", response_model=CxcParametroResponse)
def obtener_cxc(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return parametros_service.obtener_parametros_cxc(db)


@router_cxc.put("", response_model=CxcParametroResponse)
def actualizar_cxc(
    body: CxcParametroUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return parametros_service.actualizar_parametros_cxc(db, body, actor)


@router_cxp.get("", response_model=CxpParametroResponse)
def obtener_cxp(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return parametros_service.obtener_parametros_cxp(db)


@router_cxp.put("", response_model=CxpParametroResponse)
def actualizar_cxp(
    body: CxpParametroUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return parametros_service.actualizar_parametros_cxp(db, body, actor)
