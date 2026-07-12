from datetime import datetime
from pydantic import Field, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import MaintenancePriority, MaintenanceStatus, ApprovalDecision, MaintenanceLogAction
from src.domain.value_objects.snapshots import AssetSnapshot, EmployeeRequestedBySnapshot, EmployeeTechnicianSnapshot, EmployeeApproverSnapshot, EmployeePerformedBySnapshot
from src.shared.constants import MAINT_DESC_MIN_LEN, MAINT_DESC_MAX_LEN, MAINT_ATTACHMENT_URLS_MAX_ITEMS, MAINT_APPROVAL_COMMENTS_MAX_LEN, MAINT_LOG_DETAILS_MAX_LEN

class MaintenanceSubModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class MaintenanceApproval(MaintenanceSubModel):
    id: str | None = Field(default=None)
    approver_id: str = Field(...)
    approver_snapshot: EmployeeApproverSnapshot = Field(...)
    decision: ApprovalDecision = Field(...)
    comments: str = Field(default="", max_length=MAINT_APPROVAL_COMMENTS_MAX_LEN)
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(...)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(...)
    is_deleted: bool = Field(default=False)

class MaintenanceLog(MaintenanceSubModel):
    id: str | None = Field(default=None)
    action: MaintenanceLogAction = Field(...)
    performed_by: str = Field(...)
    performed_by_snapshot: EmployeePerformedBySnapshot = Field(...)
    details: str = Field(default="", max_length=MAINT_LOG_DETAILS_MAX_LEN)
    previous_status: str | None = Field(default=None)
    new_status: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(...)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(...)
    is_deleted: bool = Field(default=False)

class MaintenanceRequest(BaseEntity):
    id: str | None = Field(default=None) # Matches request_number
    request_number: str = Field(...)
    asset_id: str = Field(...)
    asset_snapshot: AssetSnapshot = Field(...)
    requested_by: str = Field(...)
    requested_by_snapshot: EmployeeRequestedBySnapshot = Field(...)
    issue_description: str = Field(..., min_length=MAINT_DESC_MIN_LEN, max_length=MAINT_DESC_MAX_LEN)
    priority: MaintenancePriority = Field(default=MaintenancePriority.MEDIUM)
    status: MaintenanceStatus = Field(default=MaintenanceStatus.PENDING_APPROVAL)
    assigned_technician_id: str | None = Field(default=None)
    assigned_technician_snapshot: EmployeeTechnicianSnapshot | None = Field(default=None)
    estimated_cost: int | None = Field(default=None, ge=0) # cents
    actual_cost: int | None = Field(default=None, ge=0) # cents
    attachment_urls: list[str] = Field(default_factory=list, max_length=MAINT_ATTACHMENT_URLS_MAX_ITEMS)
    completed_at: datetime | None = Field(default=None)
