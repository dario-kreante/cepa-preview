from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogCreate(BaseModel):
    actor: str
    action: str
    entity: str
    entity_id: str | None = None


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    entity: str
    entity_id: str | None
    created_at: datetime
