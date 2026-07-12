from pydantic import BaseModel, Field

class RoleCreate(BaseModel):
    id: str = Field(..., pattern=r"^role_[a-z0-9_]{2,20}$", description="E.g., role_manager, role_auditor")
    name: str = Field(..., min_length=2, max_length=50)
    description: str = Field("", max_length=200)
    permission_ids: list[str] = Field(default_factory=list, alias="permissionIds")

class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=50)
    description: str | None = Field(None, max_length=200)
    permission_ids: list[str] | None = Field(None, alias="permissionIds")
