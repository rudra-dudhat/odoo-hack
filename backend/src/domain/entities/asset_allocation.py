from datetime import datetime
from pydantic import Field, model_validator
from typing_extensions import Self
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import AllocationStatus, AssetCondition
from src.domain.value_objects.snapshots import AssetSnapshot, EmployeeAllocationSnapshot
from src.shared.constants import ALLOC_NOTES_MAX_LEN

class AssetAllocation(BaseEntity):
    id: str | None = Field(default=None)
    asset_id: str = Field(...)
    asset_snapshot: AssetSnapshot = Field(...)
    employee_id: str = Field(...)
    employee_snapshot: EmployeeAllocationSnapshot = Field(...)
    allocated_at: datetime = Field(default_factory=datetime.utcnow)
    expected_return_date: datetime | None = Field(default=None)
    returned_at: datetime | None = Field(default=None)
    status: AllocationStatus = Field(default=AllocationStatus.ACTIVE)
    condition_at_allocation: AssetCondition = Field(...)
    condition_at_return: AssetCondition | None = Field(default=None)
    notes: str = Field(default="", max_length=ALLOC_NOTES_MAX_LEN)

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.expected_return_date and self.expected_return_date < self.allocated_at:
            raise ValueError("expected_return_date must be greater than or equal to allocated_at")
        return self
