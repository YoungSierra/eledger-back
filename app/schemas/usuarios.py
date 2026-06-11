import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: str
    apellido: str
    password: str
    rol_id: uuid.UUID
    tercero_id: Optional[uuid.UUID] = None
    es_asesor: bool = False
    ver_solo_propios: bool = False


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    rol_id: Optional[uuid.UUID] = None
    tercero_id: Optional[uuid.UUID] = None
    es_asesor: Optional[bool] = None
    ver_solo_propios: Optional[bool] = None
    password: Optional[str] = None
    activo: Optional[bool] = None


class UsuarioResponse(BaseModel):
    id: uuid.UUID
    email: str
    nombre: str
    apellido: str
    rol_id: uuid.UUID
    tercero_id: Optional[uuid.UUID] = None
    es_asesor: bool = False
    ver_solo_propios: bool = False
    activo: bool
    ultimo_acceso: Optional[datetime] = None
    creado_en: datetime

    model_config = {"from_attributes": True}


class RolResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    es_cliente: bool
    activo: bool

    model_config = {"from_attributes": True}
