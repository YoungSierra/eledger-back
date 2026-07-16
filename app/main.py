from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import (
    auth, usuarios, periodos, empresa, roles, menu, cuentas, centros_costo,
    terceros, ope_catalogo, ope_cotizacion, ope_operacion, trm, portal, maestros, bancos, resoluciones, conceptos, inventario, consecutivos, configuracion, asientos, cxc, cxp, parametros, fac_facturas, fac_config_electronica, reportes, compras, remisiones,
)

STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(periodos.router)
app.include_router(empresa.router)
app.include_router(roles.router)
app.include_router(menu.router)
app.include_router(cuentas.router)
app.include_router(centros_costo.router)
app.include_router(terceros.router)
app.include_router(ope_catalogo.router)
app.include_router(ope_cotizacion.router)
app.include_router(ope_operacion.router)
app.include_router(trm.router)
app.include_router(portal.router)
app.include_router(maestros.router)
app.include_router(bancos.router)
app.include_router(resoluciones.router)
app.include_router(fac_config_electronica.router)
app.include_router(conceptos.router)
app.include_router(inventario.router)
app.include_router(consecutivos.router)
app.include_router(configuracion.router)
app.include_router(asientos.router)
app.include_router(cxc.router)
app.include_router(cxp.router)
app.include_router(parametros.router_cxc)
app.include_router(parametros.router_cxp)
app.include_router(fac_facturas.router)
app.include_router(reportes.router)
app.include_router(compras.router)
app.include_router(remisiones.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
