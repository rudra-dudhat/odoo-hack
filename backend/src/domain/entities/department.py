from pydantic import Field
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import DepartmentStatus
from src.shared.constants import DEPT_NAME_MIN_LEN, DEPT_NAME_MAX_LEN, DEPT_CODE_MIN_LEN, DEPT_CODE_MAX_LEN, DEPT_DESC_MAX_LEN

class Department(BaseEntity):
    id: str | None = Field(default=None)
    name: str = Field(..., min_length=DEPT_NAME_MIN_LEN, max_length=DEPT_NAME_MAX_LEN)
    code: str = Field(..., min_length=DEPT_CODE_MIN_LEN, max_length=DEPT_CODE_MAX_LEN)
    description: str = Field(default="", max_length=DEPT_DESC_MAX_LEN)
    head_employee_id: str | None = Field(default=None)
    status: DepartmentStatus = Field(default=DepartmentStatus.ACTIVE)
    employee_count: int = Field(default=0, ge=0)
    asset_count: int = Field(default=0, ge=0)
