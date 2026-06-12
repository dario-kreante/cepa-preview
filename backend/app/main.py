from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.middleware.rate_limit import limiter
from app.routers import audit_log, auth, usuarios, ingresos, pacientes, odas, consentimientos
from app.routers import farmacos
from app.routers import ept as ept_router
from app.routers import reintegros
from app.routers import controles_medicos
from app.routers import licencias
from app.routers import auditoria
from app.agendamiento import router as agendamiento_router
from app.routers import dashboard, reporte_operativo, reporte_convenio, reporte_carga, reporte_licencias, reporte_odas, reporte_adherencia, ventana_proceso
from app.routers import citas as citas_router
from app.routers import alertas as alertas_router
from app.routers import tareas as tareas_router
from app.routers import form_config as form_config_router
from app.routers import pdf_extract as pdf_extract_router
from app.routers import fichas_clinicas as fichas_clinicas_router
from app.routers import licencias_api as licencias_api_router
from app.routers import ingresos_estado as ingresos_estado_router
from app.routers import imed as imed_router
from app.routers.v2 import health_v2 as health_v2_router

app = FastAPI(title=get_settings().app_name)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
app.include_router(controles_medicos.router)
app.include_router(licencias.router)
app.include_router(auditoria.router)
app.include_router(agendamiento_router.router)
app.include_router(dashboard.router)
app.include_router(reporte_operativo.router)
app.include_router(reporte_convenio.router)
app.include_router(reporte_carga.router)
app.include_router(reporte_licencias.router)
app.include_router(reporte_odas.router)
app.include_router(reporte_adherencia.router)
app.include_router(ventana_proceso.router)
app.include_router(citas_router.router)
app.include_router(alertas_router.router)
app.include_router(tareas_router.router)
app.include_router(form_config_router.router)
app.include_router(pdf_extract_router.router)
app.include_router(fichas_clinicas_router.router)
app.include_router(licencias_api_router.router)
app.include_router(ingresos_estado_router.router)
app.include_router(imed_router.router)
app.include_router(health_v2_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
