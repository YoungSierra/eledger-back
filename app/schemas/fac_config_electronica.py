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
    # Numeración SETP de PRUEBAS de la cuenta Dataico (prefijo + número de resolución).
    # Solo se usa en ambiente PRUEBAS; en producción se usa la resolución real del sistema.
    test_prefix: Optional[str] = None
    test_resolution_number: Optional[str] = None

    # ── Credenciales de Factus (OAuth2) ──────────────────────────────────────
    # client_secret y password en None => conservar los ya guardados (la UI nunca
    # los recibe en claro, así que no puede reenviarlos).
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    # Rango de numeración YA asociado en la cuenta Factus: él asigna el consecutivo.
    numbering_range_id: Optional[str] = None

    @model_validator(mode="after")
    def credenciales_requeridas_si_activo(self) -> "ConfigElectronicaUpdate":
        if not self.activo:
            return self
        if self.proveedor == "DATAICO" and not self.account_id:
            raise ValueError("Dataico requiere el Account ID para activar la integración")
        if self.proveedor == "PTH_FACTUS":
            faltan = [n for n, v in (("Client ID", self.client_id), ("Usuario", self.username)) if not v]
            if faltan:
                raise ValueError(f"Factus requiere {' y '.join(faltan)} para activar la integración")
            if not self.numbering_range_id:
                raise ValueError("Factus requiere el ID del rango de numeración para activar la integración")
        return self


class ConfigElectronicaResponse(BaseModel):
    id: uuid.UUID
    proveedor: ProveedorType
    nombre_pth: Optional[str]
    ambiente: AmbienteType
    activo: bool
    account_id: Optional[str] = None
    base_url: Optional[str] = None
    test_prefix: Optional[str] = None
    test_resolution_number: Optional[str] = None
    # Enmascarado (••••1234). El token en claro NUNCA sale por la API.
    auth_token_mascara: Optional[str] = None
    tiene_token: bool = False
    # Factus
    client_id: Optional[str] = None
    username: Optional[str] = None
    numbering_range_id: Optional[str] = None
    client_secret_mascara: Optional[str] = None
    password_mascara: Optional[str] = None
    tiene_client_secret: bool = False
    tiene_password: bool = False
    modificado_en: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConfigElectronicaPublica(BaseModel):
    """Lo único que el print de la factura necesita saber."""
    nombre_pth: Optional[str] = None


class PruebaConexionResponse(BaseModel):
    ok: bool
    mensaje: str
