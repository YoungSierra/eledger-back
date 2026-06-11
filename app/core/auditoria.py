import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.admin import AdmAuditoria


def registrar(
    db: Session,
    tabla: str,
    registro_id: str,
    accion: str,                  # INSERT | UPDATE | DELETE
    usuario_id: uuid.UUID,
    campo: str | None = None,
    valor_anterior: Any = None,
    valor_nuevo: Any = None,
    contexto: dict | None = None,
) -> None:
    db.add(AdmAuditoria(
        tabla=tabla,
        registro_id=str(registro_id),
        accion=accion,
        campo=campo,
        valor_anterior=str(valor_anterior) if valor_anterior is not None else None,
        valor_nuevo=str(valor_nuevo) if valor_nuevo is not None else None,
        usuario_id=usuario_id,
        contexto=contexto,
    ))
