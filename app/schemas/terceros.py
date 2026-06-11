import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, field_validator


TipoPersonaType = Literal["NATURAL", "JURIDICA"]
TipoTerceroType = Literal["CLIENTE", "PROSPECTO", "PROVEEDOR", "EMPLEADO", "OTRO"]
RegimenType = Literal["SIMPLIFICADO", "ORDINARIO", "ESPECIAL"]


class TerceroCreate(BaseModel):
    nit: str
    digito_verif: Optional[str] = None
    razon_social: str
    nombre1: Optional[str] = None
    nombre2: Optional[str] = None
    apellido1: Optional[str] = None
    apellido2: Optional[str] = None
    tipo_persona: TipoPersonaType
    tipo_tercero: TipoTerceroType
    regimen: Optional[RegimenType] = None
    responsable_iva: bool = False
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None
    nombre_contacto: Optional[str] = None
    cargo_contacto: Optional[str] = None
    telefono_contacto: Optional[str] = None
    email_contacto: Optional[str] = None
    notas: Optional[str] = None
    asesor_id: Optional[uuid.UUID] = None

    @field_validator("nit")
    @classmethod
    def nit_limpio(cls, v: str) -> str:
        return v.strip().replace(".", "").replace("-", "")


class TerceroUpdate(BaseModel):
    nit: Optional[str] = None
    digito_verif: Optional[str] = None
    razon_social: Optional[str] = None
    nombre1: Optional[str] = None
    nombre2: Optional[str] = None
    apellido1: Optional[str] = None
    apellido2: Optional[str] = None
    tipo_tercero: Optional[TipoTerceroType] = None
    regimen: Optional[RegimenType] = None
    responsable_iva: Optional[bool] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None
    nombre_contacto: Optional[str] = None
    cargo_contacto: Optional[str] = None
    telefono_contacto: Optional[str] = None
    email_contacto: Optional[str] = None
    notas: Optional[str] = None
    asesor_id: Optional[uuid.UUID] = None
    activo: Optional[bool] = None

    @field_validator("nit")
    @classmethod
    def nit_limpio(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip().replace(".", "").replace("-", "")


class TerceroResponse(BaseModel):
    id: uuid.UUID
    nit: str
    digito_verif: Optional[str]
    razon_social: str
    nombre1: Optional[str]
    nombre2: Optional[str]
    apellido1: Optional[str]
    apellido2: Optional[str]
    tipo_persona: TipoPersonaType
    tipo_tercero: TipoTerceroType
    regimen: Optional[str]
    responsable_iva: bool
    email: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]
    ciudad: Optional[str]
    departamento: Optional[str]
    pais: Optional[str]
    codigo_postal: Optional[str]
    nombre_contacto: Optional[str]
    cargo_contacto: Optional[str]
    telefono_contacto: Optional[str]
    email_contacto: Optional[str]
    notas: Optional[str]
    asesor_id: Optional[uuid.UUID] = None
    asesor_nombre: Optional[str] = None
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


class TerceroSummary(BaseModel):
    id: uuid.UUID
    nit: str
    digito_verif: Optional[str]
    razon_social: str
    tipo_tercero: TipoTerceroType
    pais: Optional[str]
    ciudad: Optional[str]
    telefono: Optional[str]
    email: Optional[str]
    nombre_contacto: Optional[str]
    cargo_contacto: Optional[str]
    activo: bool

    model_config = {"from_attributes": True}
