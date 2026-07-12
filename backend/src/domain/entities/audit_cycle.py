from datetime import datetime
from pydantic import Field, BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel
from typing_extensions import Self
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import AuditCycleStatus, AssetCondition
from src.domain.value_objects.snapshots import AssetSnapshot, EmployeeAuditorSnapshot
from src.shared.constants import AUDIT_NAME_MIN_LEN, AUDIT_NAME_MAX_LEN, AUDIT_REPORT_DISCREPANCY_MAX_LEN, AUDIT_REPORT_PHOTOS_MAX_ITEMS

class AuditSubModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class AuditReport(AuditSubModel):
    id: str | None = Field(default=None)
    asset_id: str = Field(...)
    asset_snapshot: AssetSnapshot = Field(...)
    audited_by: str = Field(...)
    audited_by_snapshot: EmployeeAuditorSnapshot = Field(...)
    audited_at: datetime = Field(default_factory=datetime.utcnow)
    expected_location: str = Field(default="")
    actual_location: str = Field(default="")
    expected_condition: AssetCondition | None = Field(default=None)
    actual_condition: AssetCondition = Field(...)
    found: bool = Field(default=True)
    discrepancy_notes: str = Field(default="", max_length=AUDIT_REPORT_DISCREPANCY_MAX_LEN)
    photo_urls: list[str] = Field(default_factory=list, max_length=AUDIT_REPORT_PHOTOS_MAX_ITEMS)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(...)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(...)
    is_deleted: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_report(self) -> Self:
        condition_mismatch = (
            self.expected_condition is not None 
            and self.expected_condition != self.actual_condition
        )
        if (not self.found or condition_mismatch) and not self.discrepancy_notes:
            raise ValueError("discrepancy_notes is required if asset is not found or if there is a condition mismatch")
        return self

class AuditCycle(BaseEntity):
    id: str | None = Field(default=None) # Matches cycle_code
    cycle_code: str = Field(...)
    name: str = Field(..., min_length=AUDIT_NAME_MIN_LEN, max_length=AUDIT_NAME_MAX_LEN)
    department_ids: list[str] = Field(default_factory=list)
    category_ids: list[str] = Field(default_factory=list)
    scheduled_start: datetime = Field(...)
    scheduled_end: datetime = Field(...)
    actual_end: datetime | None = Field(default=None)
    status: AuditCycleStatus = Field(default=AuditCycleStatus.PLANNED)
    assigned_auditor_ids: list[str] = Field(default_factory=list)
    total_assets_in_scope: int = Field(default=0, ge=0)
    assets_audited: int = Field(default=0, ge=0)
    discrepancies_found: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.scheduled_end < self.scheduled_start:
            raise ValueError("scheduled_end must be greater than or equal to scheduled_start")
        return self
