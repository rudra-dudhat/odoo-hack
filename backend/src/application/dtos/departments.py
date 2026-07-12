from pydantic import BaseModel, Field
from src.domain.enums import DepartmentStatus
from src.domain.entities.department import Department

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=10)
    description: str = Field("", max_length=500)
    head_employee_id: str | None = Field(None, alias="headEmployeeId")

class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    head_employee_id: str | None = Field(None, alias="headEmployeeId")
    status: DepartmentStatus | None = None
