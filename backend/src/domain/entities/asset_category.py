from pydantic import Field
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import DepreciationMethod
from src.shared.constants import CAT_NAME_MIN_LEN, CAT_NAME_MAX_LEN, CAT_CODE_MIN_LEN, CAT_CODE_MAX_LEN, CAT_DESC_MAX_LEN

class AssetCategory(BaseEntity):
    id: str | None = Field(default=None)
    name: str = Field(..., min_length=CAT_NAME_MIN_LEN, max_length=CAT_NAME_MAX_LEN)
    code: str = Field(..., min_length=CAT_CODE_MIN_LEN, max_length=CAT_CODE_MAX_LEN)
    description: str = Field(default="", max_length=CAT_DESC_MAX_LEN)
    parent_category_id: str | None = Field(default=None)
    depreciation_method: DepreciationMethod = Field(default=DepreciationMethod.STRAIGHT_LINE)
    default_useful_life_months: int = Field(default=36, gt=0)
    asset_count: int = Field(default=0, ge=0)
