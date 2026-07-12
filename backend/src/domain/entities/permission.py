from pydantic import Field
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import PermissionModule

class Permission(BaseEntity):
    id: str | None = Field(default=None) # controlled slug, e.g. perm_asset_create
    key: str = Field(...)
    label: str = Field(...)
    module: PermissionModule = Field(...)
