from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from src.domain.enums import EmployeeStatus

class EmployeeCreate(BaseModel):
    uid: str = Field(..., description="Firebase Auth UID")
    full_name: str = Field(..., alias="fullName", min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    avatar_url: str | None = Field(None, alias="avatarUrl")
    department_id: str = Field(..., alias="departmentId")
    role_id: str = Field(..., alias="roleId")
    designation: str = Field(..., min_length=2, max_length=100)
    join_date: datetime = Field(..., alias="joinDate")

class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(None, alias="fullName", min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    avatar_url: str | None = Field(None, alias="avatarUrl")
    department_id: str | None = Field(None, alias="departmentId")
    role_id: str | None = Field(None, alias="roleId")
    designation: str | None = Field(None, min_length=2, max_length=100)
    status: EmployeeStatus | None = None
