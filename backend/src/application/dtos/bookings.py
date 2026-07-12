from datetime import datetime
from pydantic import BaseModel, Field

class BookingCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    start_time: datetime = Field(..., alias="startTime")
    end_time: datetime = Field(..., alias="endTime")
    attendee_ids: list[str] = Field(default_factory=list, alias="attendeeIds")

class BookingCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., alias="cancellationReason", min_length=5, max_length=500)
