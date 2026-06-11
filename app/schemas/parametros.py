from typing import Optional
import uuid

from pydantic import BaseModel



class CxcParametroUpdate(BaseModel):
    cuenta_clientes_id: Optional[uuid.UUID] = None
    cuenta_ingresos_id: Optional[uuid.UUID] = None
    cuenta_iva_id: Optional[uuid.UUID] = None


class CxcParametroResponse(BaseModel):
    id: uuid.UUID
    cuenta_clientes_id: Optional[uuid.UUID]
    cuenta_clientes_display: Optional[str]
    cuenta_ingresos_id: Optional[uuid.UUID]
    cuenta_ingresos_display: Optional[str]
    cuenta_iva_id: Optional[uuid.UUID]
    cuenta_iva_display: Optional[str]


class CxpParametroUpdate(BaseModel):
    cuenta_proveedores_id: Optional[uuid.UUID] = None


class CxpParametroResponse(BaseModel):
    id: uuid.UUID
    cuenta_proveedores_id: Optional[uuid.UUID]
    cuenta_proveedores_display: Optional[str]
