from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.municipios import sincronizar as sincronizar_municipio
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
    # El municipio se aplica aparte: fija el código y deriva ciudad/departamento
    # del catálogo, así los tres campos quedan siempre coherentes.
    municipio = campos.pop("municipio_codigo", None)
    for campo, valor in campos.items():
        setattr(empresa, campo, valor)
    if municipio is not None:
        try:
            sincronizar_municipio(db, empresa, municipio)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    empresa.modificado_por = actor.id
    empresa.modificado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(empresa)
    return empresa
