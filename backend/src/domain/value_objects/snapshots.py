from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class SnapshotModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class DepartmentSnapshot(SnapshotModel):
    name: str
    code: str

class AssetCategorySnapshot(SnapshotModel):
    name: str
    code: str

class RoleSnapshot(SnapshotModel):
    name: str

class CurrentHolderSnapshot(SnapshotModel):
    employee_id: str
    full_name: str

class AssetSnapshot(SnapshotModel):
    asset_tag: str
    name: str

class EmployeeAllocationSnapshot(SnapshotModel):
    full_name: str
    employee_code: str

class ResourceSnapshot(SnapshotModel):
    resource_code: str
    name: str

class EmployeeBookingSnapshot(SnapshotModel):
    full_name: str

class EmployeeRequestedBySnapshot(SnapshotModel):
    full_name: str

class EmployeeTechnicianSnapshot(SnapshotModel):
    full_name: str

class EmployeeApproverSnapshot(SnapshotModel):
    full_name: str

class EmployeePerformedBySnapshot(SnapshotModel):
    full_name: str

class EmployeeAuditorSnapshot(SnapshotModel):
    full_name: str
