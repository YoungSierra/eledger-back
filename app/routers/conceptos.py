import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UsuarioActual
from app.schemas.conceptos import ConceptoCreate, ConceptoUpdate, ConceptoResponse
from app.services import conceptos_service

router = APIRouter(prefix="/conceptos", tags=["Conceptos de causación"])


@router.get("/cxp", response_model=list[ConceptoResponse])
def listar_conceptos_cxp(
    solo_activos: bool = Query(False),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return conceptos_service.listar_conceptos(db, "cxp", solo_activos)


@router.post("/cxp", response_model=ConceptoResponse, status_code=201)
def crear_concepto_cxp(
    body: ConceptoCreate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return conceptos_service.crear_concepto(db, "cxp", body, actor)


@router.put("/cxp/{id}", response_model=ConceptoResponse)
def actualizar_concepto_cxp(
    id: uuid.UUID, body: ConceptoUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return conceptos_service.actualizar_concepto(db, id, body, actor)
