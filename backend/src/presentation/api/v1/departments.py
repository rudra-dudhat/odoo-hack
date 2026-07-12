from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.departments import DepartmentCreate, DepartmentUpdate
from src.domain.entities.employee import Employee
from src.domain.entities.department import Department
from src.domain.enums import DepartmentStatus
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.rbac import require_permission
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.department_service import DepartmentService, get_department_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[Department],
    dependencies=[Depends(require_permission("perm_departments_view"))]
)
def list_departments(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted departments"),
    status: DepartmentStatus | None = Query(default=None, description="Filter by status"),
    service: DepartmentService = Depends(get_department_service)
):
    filters = {}
    if status is not None:
        filters["status"] = status.value

    items, next_cursor = service.list_departments(
        limit=pagination.limit,
        cursor=pagination.cursor,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
        filters=filters,
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
    response_model=SingleResponse[Department],
    dependencies=[Depends(require_permission("perm_departments_view"))]
)
def get_department(
    dept_id: str = Path(..., alias="id"),
    service: DepartmentService = Depends(get_department_service)
):
    dept = service.get_by_id(dept_id)
    if not dept or dept.is_deleted:
        raise NotFoundError(f"Department {dept_id} not found")
    return SingleResponse(data=dept)

@router.post(
    "/",
    response_model=SingleResponse[Department],
    status_code=201
)
def create_department(
    payload: DepartmentCreate,
    current_user: Employee = Depends(require_permission("perm_departments_manage")),
    service: DepartmentService = Depends(get_department_service)
):
    dept = service.create_department(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        head_employee_id=payload.head_employee_id,
        actor_id=current_user.id
    )
    return SingleResponse(data=dept)

@router.put(
    "/{id}",
    response_model=SingleResponse[Department]
)
def update_department(
    payload: DepartmentUpdate,
    dept_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_departments_manage")),
    service: DepartmentService = Depends(get_department_service)
):
    dept = service.update_department(
        dept_id=dept_id,
        name=payload.name,
        description=payload.description,
        head_employee_id=payload.head_employee_id,
        status=payload.status,
        actor_id=current_user.id
    )
    return SingleResponse(data=dept)

@router.delete(
    "/{id}",
    status_code=204
)
def delete_department(
    dept_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_departments_manage")),
    service: DepartmentService = Depends(get_department_service)
):
    service.soft_delete_department(dept_id, current_user.id)

@router.post(
    "/{id}/restore",
    response_model=SingleResponse[None]
)
def restore_department(
    dept_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_departments_manage")),
    service: DepartmentService = Depends(get_department_service)
):
    service.restore_department(dept_id, current_user.id)
    return SingleResponse(data=None)
