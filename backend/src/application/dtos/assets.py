from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from src.domain.enums import DepreciationMethod, AssetCondition, AssetStatus
from src.domain.entities.asset import Asset
from src.domain.entities.asset_category import AssetCategory

class AssetCategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=10)
    description: str = Field("", max_length=500)
    parent_category_id: str | None = Field(None, alias="parentCategoryId")
    depreciation_method: DepreciationMethod = Field(default=DepreciationMethod.STRAIGHT_LINE, alias="depreciationMethod")
    default_useful_life_months: int = Field(default=60, alias="defaultUsefulLifeMonths", ge=1)

class AssetCategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    parent_category_id: str | None = Field(None, alias="parentCategoryId")
    depreciation_method: DepreciationMethod | None = Field(None, alias="depreciationMethod")
    default_useful_life_months: int | None = Field(None, alias="defaultUsefulLifeMonths", ge=1)

class AssetCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    category_id: str = Field(..., alias="categoryId")
    department_id: str = Field(..., alias="departmentId")
    serial_number: str = Field(..., alias="serialNumber", min_length=2, max_length=50)
    manufacturer: str = Field(..., min_length=2, max_length=50)
    model: str = Field(..., min_length=2, max_length=50)
    purchase_date: datetime | None = Field(None, alias="purchaseDate")
    purchase_cost: int = Field(..., alias="purchaseCost", ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    warranty_expiry_date: datetime | None = Field(None, alias="warrantyExpiryDate")
    location: str = Field(..., min_length=2, max_length=100)
    image_urls: list[str] = Field(default_factory=list, alias="imageUrls")
    condition: AssetCondition = AssetCondition.GOOD

class AssetUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    category_id: str | None = Field(None, alias="categoryId")
    department_id: str | None = Field(None, alias="departmentId")
    serial_number: str | None = Field(None, alias="serialNumber", min_length=2, max_length=50)
    manufacturer: str | None = Field(None, min_length=2, max_length=50)
    model: str | None = Field(None, min_length=2, max_length=50)
    purchase_date: datetime | None = Field(None, alias="purchaseDate")
    purchase_cost: int | None = Field(None, alias="purchaseCost", ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    warranty_expiry_date: datetime | None = Field(None, alias="warrantyExpiryDate")
    location: str | None = Field(None, min_length=2, max_length=100)
    image_urls: list[str] | None = Field(None, alias="imageUrls")
    condition: AssetCondition | None = None

class AssetRetireRequest(BaseModel):
    note: str = Field(..., min_length=5, max_length=500)

class AssetLostRequest(BaseModel):
    note: str = Field(..., min_length=5, max_length=500)

class AssetResponse(BaseModel):
    id: str
    asset_tag: str = Field(..., alias="assetTag")
    name: str
    category_id: str = Field(..., alias="categoryId")
    category_snapshot: Any = Field(..., alias="categorySnapshot")
    department_id: str = Field(..., alias="departmentId")
    department_snapshot: Any = Field(..., alias="departmentSnapshot")
    serial_number: str = Field(..., alias="serialNumber")
    manufacturer: str
    model: str
    purchase_date: datetime | None = Field(None, alias="purchaseDate")
    purchase_cost: int | None = Field(None, alias="purchaseCost")
    currency: str | None = None
    warranty_expiry_date: datetime | None = Field(None, alias="warrantyExpiryDate")
    location: str
    image_urls: list[str] = Field(default_factory=list, alias="imageUrls")
    status: AssetStatus
    condition: AssetCondition
    current_allocation_id: str | None = Field(None, alias="currentAllocationId")
    current_holder_snapshot: Any | None = Field(None, alias="currentHolderSnapshot")
    
    @classmethod
    def from_entity(cls, entity: Asset, include_financial: bool = False) -> "AssetResponse":
        data = entity.model_dump(by_alias=True)
        if not include_financial:
            data["purchaseCost"] = None
            data["currency"] = None
        return cls.model_validate(data)
