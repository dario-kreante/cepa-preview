from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    rol: str | None
    action: str
    entity: str
    entity_id: str | None
    valor_anterior: str | None
    valor_nuevo: str | None
    created_at: datetime
