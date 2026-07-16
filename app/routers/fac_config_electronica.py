from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.fac_config_electronica import (
    ConfigElectronicaPublica, ConfigElectronicaResponse,
    ConfigElectronicaUpdate, PruebaConexionResponse,
)
from app.services import fac_config_electronica_service as svc

router = APIRouter(prefix="/facturacion/config-electronica", tags=["Facturación electrónica"])


@router.get("/publica", response_model=ConfigElectronicaPublica)
def publica(db: Session = Depends(get_db)):
    """Solo el nombre del PTH, para el pie del print de la factura. Sin auth."""
    cfg = svc.obtener(db)
    return ConfigElectronicaPublica(nombre_pth=cfg.nombre_pth if cfg else None)


@router.get("", response_model=ConfigElectronicaResponse | None)
def obtener(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.obtener_para_api(db)


@router.put("", response_model=ConfigElectronicaResponse)
def guardar(
    body: ConfigElectronicaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return svc.guardar(db, body, actor)


@router.post("/probar", response_model=PruebaConexionResponse)
def probar(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    ok, mensaje = svc.probar_conexion(db)
    return PruebaConexionResponse(ok=ok, mensaje=mensaje)
