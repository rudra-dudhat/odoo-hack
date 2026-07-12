from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import ResourceType, ResourceStatus
from src.shared.constants import RESOURCE_NAME_MIN_LEN, RESOURCE_NAME_MAX_LEN, RESOURCE_AMENITIES_MAX_ITEMS, RESOURCE_IMAGE_URLS_MAX_ITEMS, RESOURCE_DEFAULT_MIN_DURATION, RESOURCE_DEFAULT_MAX_DURATION, RESOURCE_DEFAULT_ADVANCE_DAYS

class BookingRules(BaseModel):
    min_duration_minutes: int = Field(default=RESOURCE_DEFAULT_MIN_DURATION, gt=0)
    max_duration_minutes: int = Field(default=RESOURCE_DEFAULT_MAX_DURATION, gt=0)
    advance_booking_days: int = Field(default=RESOURCE_DEFAULT_ADVANCE_DAYS, gt=0)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class SharedResource(BaseEntity):
    id: str | None = Field(default=None) # Matches resource_code
    resource_code: str = Field(...)
    name: str = Field(..., min_length=RESOURCE_NAME_MIN_LEN, max_length=RESOURCE_NAME_MAX_LEN)
    type: ResourceType = Field(...)
    capacity: int | None = Field(default=None, gt=0)
    location: str = Field(default="")
    amenities: list[str] = Field(default_factory=list, max_length=RESOURCE_AMENITIES_MAX_ITEMS)
    image_urls: list[str] = Field(default_factory=list, max_length=RESOURCE_IMAGE_URLS_MAX_ITEMS)
    status: ResourceStatus = Field(default=ResourceStatus.ACTIVE)
    booking_rules: BookingRules = Field(default_factory=BookingRules)
