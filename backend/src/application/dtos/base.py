from typing import Generic, TypeVar, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class BaseResponse(BaseModel):
    success: bool = True

class SingleResponse(BaseResponse, Generic[T]):
    data: T
    meta: dict[str, Any] | None = None

class PaginatedMeta(BaseModel):
    next_cursor: str | None = Field(default=None, alias="nextCursor")
    has_more: bool = Field(default=False, alias="hasMore")

class ListResponse(BaseResponse, Generic[T]):
    data: list[T]
    meta: PaginatedMeta
