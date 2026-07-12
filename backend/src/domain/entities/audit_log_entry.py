from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from src.domain.enums import AuditLogAction

class AuditLogEntry(BaseModel):
    id: str | None = Field(default=None)
    entity_type: str = Field(...)
    entity_id: str = Field(...)
    action: AuditLogAction = Field(...)
    performed_by: str = Field(...) # employeeId or "system"
    changed_fields: list[str] = Field(default_factory=list)
    before_snapshot: dict | None = Field(default=None)
    after_snapshot: dict | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: str | None = Field(default=None)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
