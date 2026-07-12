from datetime import datetime
from pydantic import Field
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import DashboardScope, AssetStatus, MaintenancePriority

def default_assets_by_status():
    return {status.value: 0 for status in AssetStatus}

def default_maintenance_by_priority():
    return {priority.value: 0 for priority in MaintenancePriority}

class DashboardAggregate(BaseEntity):
    id: str | None = Field(default=None) # E.g., global_kpis, dept_{id}, daily_{YYYY-MM-DD}
    scope: DashboardScope = Field(...)
    scope_ref_id: str | None = Field(default=None)
    total_assets: int = Field(default=0, ge=0)
    assets_by_status: dict[str, int] = Field(default_factory=default_assets_by_status)
    total_active_allocations: int = Field(default=0, ge=0)
    total_overdue_allocations: int = Field(default=0, ge=0)
    total_bookings_today: int = Field(default=0, ge=0)
    open_maintenance_requests: int = Field(default=0, ge=0)
    maintenance_by_priority: dict[str, int] = Field(default_factory=default_maintenance_by_priority)
    audit_compliance_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    pending_notifications_count: int = Field(default=0, ge=0)
    last_computed_at: datetime = Field(default_factory=datetime.utcnow)
