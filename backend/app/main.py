from fastapi import FastAPI

from app.config import get_settings
from app.routers import audit_log

app = FastAPI(title=get_settings().app_name)
app.include_router(audit_log.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
