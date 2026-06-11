import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class EmpresaUpdate(BaseModel):
    razon_social: Optional[str] = None
    nit: Optional[str] = None
    digito_verif: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    regimen: Optional[str] = None
    responsable_iva: Optional[bool] = None
    logo_url: Optional[str] = None
    actividad_economica_codigo: Optional[str] = None
    actividad_economica_descripcion: Optional[str] = None


class EmpresaResponse(BaseModel):
    id: uuid.UUID
    razon_social: str
    nit: str
    digito_verif: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    regimen: Optional[str] = None
    responsable_iva: bool
    logo_url: Optional[str] = None
    actividad_economica_codigo: Optional[str] = None
    actividad_economica_descripcion: Optional[str] = None
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


class EmpresaPublica(BaseModel):
    razon_social: str
    logo_url: Optional[str] = None

    model_config = {"from_attributes": True}
