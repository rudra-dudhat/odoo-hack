from pydantic import BaseModel, Field
from src.domain.enums import DashboardScope

class DashboardRecomputeRequest(BaseModel):
    scope: DashboardScope
    scope_ref_id: str | None = Field(None, alias="scopeRefId", description="Required for department scope (departmentId)")
