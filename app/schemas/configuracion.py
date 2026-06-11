from typing import Optional
from pydantic import BaseModel


class ConfiguracionUpdate(BaseModel):
    valor: str


class ConfiguracionResponse(BaseModel):
    clave: str
    valor: str
    tipo: str
    descripcion: Optional[str]
    model_config = {"from_attributes": True}
