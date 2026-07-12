from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.roles import RoleCreate, RoleUpdate
from src.domain.entities.employee import Employee
from src.domain.entities.role import Role
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.rbac import require_permission
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.role_service import RoleService, get_role_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[Role],
    dependencies=[Depends(require_permission("perm_roles_view"))]
)
def list_roles(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted roles"),
    service: RoleService = Depends(get_role_service)
):
    items, next_cursor = service.list_roles(
        limit=pagination.limit,
        cursor=pagination.cursor,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
        include_deleted=includeDeleted
    )
    return ListResponse(
        data=items,
        meta=PaginatedMeta(
            nextCursor=next_cursor,
            hasMore=next_cursor is not None
        )
    )

@router.get(
    "/{id}",
    response_model=SingleResponse[Role],
    dependencies=[Depends(require_permission("perm_roles_view"))]
)
def get_role(
    role_id: str = Path(..., alias="id"),
    service: RoleService = Depends(get_role_service)
):
    role = service.get_role_by_id(role_id)
    if not role or role.is_deleted:
        raise NotFoundError(f"Role {role_id} not found")
    return SingleResponse(data=role)

@router.post(
    "/",
    response_model=SingleResponse[Role],
    status_code=201
)
def create_role(
    payload: RoleCreate,
    current_user: Employee = Depends(require_permission("perm_roles_manage")),
    service: RoleService = Depends(get_role_service)
):
    role = service.create_role(
        role_id=payload.id,
        name=payload.name,
        description=payload.description,
        permission_ids=payload.permission_ids,
        actor_id=current_user.id
    )
    return SingleResponse(data=role)

@router.put(
    "/{id}",
    response_model=SingleResponse[Role]
)
def update_role(
    payload: RoleUpdate,
    role_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_roles_manage")),
    service: RoleService = Depends(get_role_service)
):
    role = service.update_role(
        role_id=role_id,
        name=payload.name,
        description=payload.description,
        permission_ids=payload.permission_ids,
        actor_id=current_user.id
    )
    return SingleResponse(data=role)

@router.delete(
    "/{id}",
    status_code=204
)
def delete_role(
    role_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_roles_manage")),
    service: RoleService = Depends(get_role_service)
):
    service.soft_delete_role(role_id, current_user.id)

@router.post(
    "/{id}/restore",
    response_model=SingleResponse[None]
)
def restore_role(
    role_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_roles_manage")),
    service: RoleService = Depends(get_role_service)
):
    service.restore_role(role_id, current_user.id)
    return SingleResponse(data=None)
