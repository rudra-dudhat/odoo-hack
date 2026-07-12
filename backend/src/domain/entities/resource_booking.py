from datetime import datetime
from pydantic import Field, model_validator
from typing_extensions import Self
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import BookingStatus
from src.domain.value_objects.snapshots import ResourceSnapshot, EmployeeBookingSnapshot
from src.shared.constants import BOOKING_TITLE_MIN_LEN, BOOKING_TITLE_MAX_LEN, BOOKING_ATTENDEES_MAX_ITEMS

class ResourceBooking(BaseEntity):
    id: str | None = Field(default=None)
    resource_id: str = Field(...)
    resource_snapshot: ResourceSnapshot = Field(...)
    employee_id: str = Field(...)
    employee_snapshot: EmployeeBookingSnapshot = Field(...)
    title: str = Field(..., min_length=BOOKING_TITLE_MIN_LEN, max_length=BOOKING_TITLE_MAX_LEN)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    attendee_ids: list[str] = Field(default_factory=list, max_length=BOOKING_ATTENDEES_MAX_ITEMS)
    status: BookingStatus = Field(default=BookingStatus.CONFIRMED)
    cancellation_reason: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_booking(self) -> Self:
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be strictly less than end_time")
        if self.status == BookingStatus.CANCELLED and not self.cancellation_reason:
            raise ValueError("cancellation_reason is required when booking status is cancelled")
        return self
