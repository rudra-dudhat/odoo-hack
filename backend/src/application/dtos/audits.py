from datetime import datetime
from pydantic import BaseModel, Field
from src.domain.enums import AssetCondition

class AuditCycleCreate(BaseModel):
    cycle_code: str = Field(..., alias="cycleCode", pattern=r"^AC-\d{4}-Q[1-4]$", description="E.g. AC-2026-Q3")
    name: str = Field(..., min_length=3, max_length=100)
    department_ids: list[str] = Field(..., alias="departmentIds")
    category_ids: list[str] = Field(default_factory=list, alias="categoryIds")
    scheduled_start: datetime = Field(..., alias="scheduledStart")
    scheduled_end: datetime = Field(..., alias="scheduledEnd")
    assigned_auditor_ids: list[str] = Field(..., alias="assignedAuditorIds")

class AuditReportSubmit(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    actual_location: str = Field(..., alias="actualLocation", min_length=2, max_length=100)
    actual_condition: AssetCondition = Field(..., alias="actualCondition")
    found: bool
    discrepancy_notes: str = Field("", alias="discrepancyNotes", max_length=500)
    photo_urls: list[str] = Field(default_factory=list, alias="photoUrls")
