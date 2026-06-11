from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    es_cliente: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UsuarioActual(BaseModel):
    id: str
    email: str
    nombre: str
    apellido: str
    rol_id: str
    ver_solo_propios: bool = False
    es_asesor: bool = False
    permisos: list[str] = []

    model_config = {"from_attributes": True}
