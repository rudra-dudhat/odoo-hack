from pydantic import Field
from src.domain.entities.base_entity import BaseEntity
from src.shared.constants import ROLE_NAME_MIN_LEN, ROLE_NAME_MAX_LEN, ROLE_DESC_MAX_LEN, ROLE_PERMISSIONS_MAX_ITEMS

class Role(BaseEntity):
    id: str | None = Field(default=None) # controlled slug, e.g. role_admin
    name: str = Field(..., min_length=ROLE_NAME_MIN_LEN, max_length=ROLE_NAME_MAX_LEN)
    description: str = Field(default="", max_length=ROLE_DESC_MAX_LEN)
    permission_ids: list[str] = Field(default_factory=list, max_length=ROLE_PERMISSIONS_MAX_ITEMS)
    is_system_role: bool = Field(default=False)
