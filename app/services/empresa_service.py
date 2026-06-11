from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.admin import AdmEmpresa
from app.schemas.auth import UsuarioActual
from app.schemas.empresa import EmpresaUpdate


def obtener_empresa(db: Session) -> AdmEmpresa:
    empresa = db.query(AdmEmpresa).filter(AdmEmpresa.activo == True).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no configurada",
        )
    return empresa


def obtener_empresa_publica(db: Session) -> AdmEmpresa | None:
    return db.query(AdmEmpresa).filter(AdmEmpresa.activo == True).first()


def actualizar_empresa(db: Session, data: EmpresaUpdate, actor: UsuarioActual) -> AdmEmpresa:
    empresa = db.query(AdmEmpresa).filter(AdmEmpresa.activo == True).first()

    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no configurada — contacta al administrador del sistema",
        )

    campos = data.model_dump(exclude_none=True)
    for campo, valor in campos.items():
        setattr(empresa, campo, valor)

    empresa.modificado_por = actor.id
    empresa.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(empresa)
    return empresa
