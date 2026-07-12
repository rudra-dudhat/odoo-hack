from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class Counter(BaseModel):
    id: str | None = Field(default=None) # E.g., assets, resources, maintenanceRequests, auditCycles
    value: int = Field(..., ge=0)
    prefix: str = Field(...)
    padding: int = Field(...)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
