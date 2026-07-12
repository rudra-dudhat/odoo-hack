from pydantic import BaseModel, Field
from src.domain.enums import MaintenancePriority, MaintenanceStatus

class MaintenanceRequestCreate(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    issue_description: str = Field(..., alias="issueDescription", min_length=5, max_length=500)
    priority: MaintenancePriority = MaintenancePriority.MEDIUM

class MaintenanceApproveRequest(BaseModel):
    comments: str = Field(..., min_length=2, max_length=500)

class MaintenanceRejectRequest(BaseModel):
    comments: str = Field(..., min_length=2, max_length=500)

class MaintenanceAssignRequest(BaseModel):
    technician_id: str = Field(..., alias="technicianId")

class MaintenanceProgressRequest(BaseModel):
    status: MaintenanceStatus
    actual_cost: int | None = Field(None, alias="actualCost", ge=0)
