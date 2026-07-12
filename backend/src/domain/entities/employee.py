from datetime import datetime
from pydantic import Field, EmailStr
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import EmployeeStatus
from src.domain.value_objects.snapshots import DepartmentSnapshot, RoleSnapshot
from src.shared.constants import EMP_NAME_MIN_LEN, EMP_NAME_MAX_LEN, EMP_DESIGNATION_MAX_LEN

class Employee(BaseEntity):
    id: str | None = Field(default=None) # Matches Firebase Auth UID
    full_name: str = Field(..., min_length=EMP_NAME_MIN_LEN, max_length=EMP_NAME_MAX_LEN)
    email: EmailStr = Field(...)
    phone: str = Field(default="")
    avatar_url: str | None = Field(default=None)
    department_id: str = Field(...)
    department_snapshot: DepartmentSnapshot = Field(...)
    role_id: str = Field(...)
    role_snapshot: RoleSnapshot = Field(...)
    designation: str = Field(default="", max_length=EMP_DESIGNATION_MAX_LEN)
    employee_code: str = Field(...)
    join_date: datetime = Field(...)
    status: EmployeeStatus = Field(default=EmployeeStatus.ACTIVE)
