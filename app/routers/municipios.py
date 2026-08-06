"""Catálogos geográficos y de identificación.

Solo lectura: son catálogos estáticos que se cargan por seed (o viven en
código). Alimentan los selectores de empresa y terceros y el mapeo a la DIAN.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.catalogos_dian import TIPOS_DOCUMENTO
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.admin import AdmMunicipio, AdmPais
from app.schemas.auth import UsuarioActual

router = APIRouter(prefix="/municipios", tags=["Municipios (DIVIPOLA)"])
router_paises = APIRouter(prefix="/paises", tags=["Países y catálogos DIAN"])


class PaisResponse(BaseModel):
    codigo: str
    nombre: str

    model_config = {"from_attributes": True}


@router_paises.get("", response_model=list[PaisResponse])
def listar_paises(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    return db.query(AdmPais).order_by(AdmPais.nombre).all()


@router_paises.get("/tipos-documento", response_model=list[PaisResponse])
def listar_tipos_documento(actor: UsuarioActual = Depends(get_current_user)):
    """Catálogo DIAN de tipos de documento de identificación."""
    return [PaisResponse(**t) for t in TIPOS_DOCUMENTO]


class DepartamentoResponse(BaseModel):
    codigo: str
    nombre: str


class MunicipioResponse(BaseModel):
    codigo: str
    nombre: str
    depto_codigo: str
    depto_nombre: str

    model_config = {"from_attributes": True}


@router.get("/departamentos", response_model=list[DepartamentoResponse])
def listar_departamentos(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    filas = (
        db.query(AdmMunicipio.depto_codigo, AdmMunicipio.depto_nombre)
        .distinct()
        .order_by(AdmMunicipio.depto_nombre)
        .all()
    )
    return [DepartamentoResponse(codigo=c, nombre=n) for c, n in filas]


@router.get("", response_model=list[MunicipioResponse])
def listar_municipios(
    departamento: str | None = Query(None, description="Código DANE del departamento (2 dígitos)"),
    q: str | None = Query(None, description="Filtro por nombre"),
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(get_current_user),
):
    query = db.query(AdmMunicipio)
    if departamento:
        query = query.filter(AdmMunicipio.depto_codigo == departamento)
    if q:
        query = query.filter(AdmMunicipio.nombre.ilike(f"%{q.strip()}%"))
    return query.order_by(AdmMunicipio.depto_nombre, AdmMunicipio.nombre).limit(1500).all()
