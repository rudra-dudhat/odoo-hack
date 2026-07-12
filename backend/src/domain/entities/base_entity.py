from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class BaseEntity(BaseModel):
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
    created_by: str | None = Field(default=None)
    updated_by: str | None = Field(default=None)
    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = Field(default=None)
    deleted_by: str | None = Field(default=None)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
