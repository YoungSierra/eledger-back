import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, model_validator

ProveedorType = Literal["DATAICO", "PTH_APIFE", "PTH_SIECOM", "PTH_FACTUS", "DIAN_DIRECTO"]
AmbienteType = Literal["PRUEBAS", "PRODUCCION"]


class ConfigElectronicaUpdate(BaseModel):
    proveedor: ProveedorType
    nombre_pth: Optional[str] = None
    ambiente: AmbienteType = "PRUEBAS"
    activo: bool = True
    # Credenciales de Dataico. auth_token en None => conservar el ya guardado
    # (la UI nunca recibe el token en claro, así que no puede reenviarlo).
    account_id: Optional[str] = None
    auth_token: Optional[str] = None
    # Vacío => producción. La URL de habilitación la entrega Dataico; no está
    # publicada, así que no se adivina aquí.
    base_url: Optional[str] = None

    @model_validator(mode="after")
    def credenciales_requeridas_si_activo(self) -> "ConfigElectronicaUpdate":
        if self.activo and self.proveedor == "DATAICO" and not self.account_id:
            raise ValueError("Dataico requiere el Account ID para activar la integración")
        return self


class ConfigElectronicaResponse(BaseModel):
    id: uuid.UUID
    proveedor: ProveedorType
    nombre_pth: Optional[str]
    ambiente: AmbienteType
    activo: bool
    account_id: Optional[str] = None
    base_url: Optional[str] = None
    # Enmascarado (••••1234). El token en claro NUNCA sale por la API.
    auth_token_mascara: Optional[str] = None
    tiene_token: bool = False
    modificado_en: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConfigElectronicaPublica(BaseModel):
    """Lo único que el print de la factura necesita saber."""
    nombre_pth: Optional[str] = None


class PruebaConexionResponse(BaseModel):
    ok: bool
    mensaje: str
