from fastapi import FastAPI

from app.config import get_settings
from app.routers import audit_log, auth, usuarios, ingresos, pacientes, odas, consentimientos
from app.routers import farmacos
from app.routers import ept as ept_router
from app.routers import reintegros

app = FastAPI(title=get_settings().app_name)
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(audit_log.router)
app.include_router(ingresos.router)
app.include_router(pacientes.router)
app.include_router(odas.router)
app.include_router(consentimientos.router)
app.include_router(farmacos.router)
app.include_router(ept_router.router)
app.include_router(reintegros.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
