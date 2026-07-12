from fastapi import Query, HTTPException
from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    cursor: str | None = Field(default=None)
    sort_by: str | None = Field(default=None)
    sort_dir: str = Field(default="asc")

def get_pagination_params(
    limit: int = Query(default=25, ge=1, le=100, description="Number of results to return (max 100)"),
    cursor: str | None = Query(default=None, description="Opaque cursor string for next page"),
    sortBy: str | None = Query(default=None, alias="sortBy", description="Field name to sort by"),
    sortDir: str = Query(default="asc", alias="sortDir", description="Sort direction: 'asc' or 'desc'")
) -> PaginationParams:
    """
    FastAPI dependency to extract pagination query parameters.
    """
    clean_sort_dir = sortDir.lower()
    if clean_sort_dir not in ("asc", "desc"):
        clean_sort_dir = "asc"
        
    return PaginationParams(
        limit=limit,
        cursor=cursor,
        sort_by=sortBy,
        sort_dir=clean_sort_dir
    )
