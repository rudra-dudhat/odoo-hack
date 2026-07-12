from pydantic import BaseModel, Field

class BookingRulesDTO(BaseModel):
    min_duration_minutes: int = Field(default=30, alias="minDurationMinutes", ge=1)
    max_duration_minutes: int = Field(default=480, alias="maxDurationMinutes", ge=1)
    advance_booking_days: int = Field(default=30, alias="advanceBookingDays", ge=1)

class SharedResourceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    type: str = Field(..., min_length=2, max_length=50, description="E.g., meeting_room, vehicle")
    capacity: int | None = Field(None, ge=1)
    location: str = Field(..., min_length=2, max_length=100)
    amenities: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list, alias="imageUrls")
    booking_rules: BookingRulesDTO = Field(..., alias="bookingRules")

class SharedResourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    type: str | None = Field(None, min_length=2, max_length=50)
    capacity: int | None = Field(None, ge=1)
    location: str | None = Field(None, min_length=2, max_length=100)
    amenities: list[str] | None = None
    image_urls: list[str] | None = Field(None, alias="imageUrls")
    booking_rules: BookingRulesDTO | None = Field(None, alias="bookingRules")
