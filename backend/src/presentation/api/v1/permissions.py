from fastapi import APIRouter, Depends, Query
from src.application.dtos.base import ListResponse, PaginatedMeta
from src.domain.entities.permission import Permission
from src.presentation.dependencies.rbac import require_permission
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.domain.repositories.permission_repository import PermissionRepository
from src.infrastructure.firestore.repositories.firestore_permission_repository import get_permission_repository

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[Permission],
    dependencies=[Depends(require_permission("perm_roles_view"))]
)
def list_permissions(
    pagination: PaginationParams = Depends(get_pagination_params),
    repo: PermissionRepository = Depends(get_permission_repository)
):
    items, next_cursor = repo.list(
        limit=pagination.limit,
        cursor=pagination.cursor,
        sort_by="key",
        sort_dir="asc"
    )
    return ListResponse(
        data=items,
        meta=PaginatedMeta(
            nextCursor=next_cursor,
            hasMore=next_cursor is not None
        )
    )
