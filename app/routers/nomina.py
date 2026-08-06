import uuid
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.nomina import (
    NomPeriodoCreate, NomPeriodoUpdate, AnularNominaRequest,
    NomPeriodoResponse, NomListResponse, ImportarExcelResponse,
)
from app.services import nomina_service

router = APIRouter(prefix="/nomina", tags=["Nómina electrónica"])


@router.get("/plantilla-excel")
def plantilla_excel(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    data = nomina_service.generar_plantilla_excel()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plantilla_nomina.xlsx"'},
    )


@router.post("/importar-excel", response_model=ImportarExcelResponse)
async def importar_excel(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    contenido = await archivo.read()
    return nomina_service.importar_excel(contenido)


@router.get("", response_model=NomListResponse)
def listar(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    estado: str | None = Query(None),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return nomina_service.listar(db, pagina, por_pagina, estado)


@router.post("", response_model=NomPeriodoResponse, status_code=201)
def crear(
    body: NomPeriodoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return nomina_service.crear(db, body, actor)


@router.get("/{id}", response_model=NomPeriodoResponse)
def obtener(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return nomina_service.obtener(db, id)


@router.put("/{id}", response_model=NomPeriodoResponse)
def actualizar(
    id: uuid.UUID,
    body: NomPeriodoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return nomina_service.actualizar(db, id, body, actor)


@router.delete("/{id}", status_code=204)
def eliminar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    nomina_service.eliminar(db, id, actor)


@router.post("/{id}/generar", response_model=NomPeriodoResponse)
def generar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return nomina_service.generar(db, id, actor)


@router.post("/{id}/enviar", response_model=NomPeriodoResponse)
def enviar(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return nomina_service.enviar(db, id, actor)


@router.post("/{id}/anular", response_model=NomPeriodoResponse)
def anular(
    id: uuid.UUID,
    body: AnularNominaRequest,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return nomina_service.anular(db, id, body, actor)
