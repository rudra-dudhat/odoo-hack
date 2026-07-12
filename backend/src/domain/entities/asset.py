from datetime import datetime
from pydantic import Field
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import AssetStatus, AssetCondition
from src.domain.value_objects.snapshots import DepartmentSnapshot, AssetCategorySnapshot, CurrentHolderSnapshot
from src.shared.constants import ASSET_NAME_MIN_LEN, ASSET_NAME_MAX_LEN, ASSET_MANUFACTURER_MAX_LEN, ASSET_MODEL_MAX_LEN, ASSET_IMAGE_URLS_MAX_ITEMS

class Asset(BaseEntity):
    id: str | None = Field(default=None) # Matches asset_tag
    asset_tag: str = Field(...)
    name: str = Field(..., min_length=ASSET_NAME_MIN_LEN, max_length=ASSET_NAME_MAX_LEN)
    category_id: str = Field(...)
    category_snapshot: AssetCategorySnapshot = Field(...)
    department_id: str = Field(...)
    department_snapshot: DepartmentSnapshot = Field(...)
    serial_number: str = Field(default="")
    manufacturer: str = Field(default="", max_length=ASSET_MANUFACTURER_MAX_LEN)
    model: str = Field(default="", max_length=ASSET_MODEL_MAX_LEN)
    purchase_date: datetime | None = Field(default=None)
    purchase_cost: int = Field(default=0, ge=0) # in cents
    currency: str = Field(default="USD", max_length=3)
    warranty_expiry_date: datetime | None = Field(default=None)
    location: str = Field(default="")
    image_urls: list[str] = Field(default_factory=list, max_length=ASSET_IMAGE_URLS_MAX_ITEMS)
    status: AssetStatus = Field(default=AssetStatus.AVAILABLE)
    condition: AssetCondition = Field(default=AssetCondition.GOOD)
    current_allocation_id: str | None = Field(default=None)
    current_holder_snapshot: CurrentHolderSnapshot | None = Field(default=None)
