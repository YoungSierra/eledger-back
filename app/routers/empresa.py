from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permisos import require_permission
from app.schemas.auth import UsuarioActual
from app.schemas.empresa import EmpresaPublica, EmpresaResponse, EmpresaUpdate
from app.services import empresa_service

router = APIRouter(prefix="/empresa", tags=["Empresa"])

STATIC_DIR = Path(__file__).parent.parent.parent / "static"
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"}
MAX_SIZE = 2 * 1024 * 1024  # 2 MB


@router.get("/publica", response_model=EmpresaPublica | None)
def publica(db: Session = Depends(get_db)):
    """Endpoint público — sin autenticación. Usado por el login para mostrar el logo."""
    return empresa_service.obtener_empresa_publica(db)


@router.get("", response_model=EmpresaResponse)
def obtener(
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "ver")),
):
    return empresa_service.obtener_empresa(db)


@router.put("", response_model=EmpresaResponse)
def actualizar(
    body: EmpresaUpdate,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "editar")),
):
    return empresa_service.actualizar_empresa(db, body, actor)


@router.post("/logo", response_model=dict)
async def subir_logo(
    file: UploadFile,
    db: Session = Depends(get_db),
    actor: UsuarioActual = Depends(require_permission("administracion", "editar")),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido: {file.content_type}",
        )

    contenido = await file.read()
    if len(contenido) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo supera el tamaño máximo de 2 MB",
        )

    ext = Path(file.filename or "logo.png").suffix or ".png"
    nombre = f"logo{ext}"
    destino = STATIC_DIR / nombre
    destino.write_bytes(contenido)

    logo_url = f"http://localhost:8001/static/{nombre}"

    empresa = empresa_service.obtener_empresa(db)
    empresa.logo_url = logo_url
    db.commit()

    return {"logo_url": logo_url}
