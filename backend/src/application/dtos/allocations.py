from datetime import datetime
from pydantic import BaseModel, Field
from src.domain.enums import AssetCondition

class AllocationCreate(BaseModel):
    employee_id: str = Field(..., alias="employeeId")
    expected_return_date: datetime | None = Field(None, alias="expectedReturnDate")
    notes: str = Field("", max_length=500)

class AllocationReturnRequest(BaseModel):
    condition_at_return: AssetCondition = Field(..., alias="conditionAtReturn")
    notes: str = Field("", max_length=500)

class AllocationLostRequest(BaseModel):
    notes: str = Field(..., min_length=5, max_length=500)
