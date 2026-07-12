from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.employees import EmployeeCreate, EmployeeUpdate
from src.domain.entities.employee import Employee
from src.domain.enums import EmployeeStatus
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.rbac import require_permission
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.employee_service import EmployeeService, get_employee_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[Employee],
    dependencies=[Depends(require_permission("perm_employees_view"))]
)
def list_employees(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted employees"),
    status: EmployeeStatus | None = Query(default=None, description="Filter by status"),
    departmentId: str | None = Query(default=None, alias="departmentId", description="Filter by department"),
    roleId: str | None = Query(default=None, alias="roleId", description="Filter by role"),
    service: EmployeeService = Depends(get_employee_service)
):
    filters = {}
    if status is not None:
        filters["status"] = status.value
    if departmentId is not None:
        filters["departmentId"] = departmentId
    if roleId is not None:
        filters["roleId"] = roleId

    items, next_cursor = service.list_employees(
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
    "/me",
    response_model=SingleResponse[Employee]
)
def get_current_employee_profile(
    current_user: Employee = Depends(get_current_employee)
):
    return SingleResponse(data=current_user)

@router.get(
    "/{id}",
    response_model=SingleResponse[Employee],
    dependencies=[Depends(require_permission("perm_employees_view"))]
)
def get_employee(
    emp_id: str = Path(..., alias="id"),
    service: EmployeeService = Depends(get_employee_service)
):
    emp = service.get_by_id(emp_id)
    if not emp or emp.is_deleted:
        raise NotFoundError(f"Employee {emp_id} not found")
    return SingleResponse(data=emp)

@router.post(
    "/",
    response_model=SingleResponse[Employee],
    status_code=201
)
def create_employee(
    payload: EmployeeCreate,
    current_user: Employee = Depends(require_permission("perm_employees_manage")),
    service: EmployeeService = Depends(get_employee_service)
):
    emp = service.create_employee(
        uid=payload.uid,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        avatar_url=payload.avatar_url,
        department_id=payload.department_id,
        role_id=payload.role_id,
        designation=payload.designation,
        join_date=payload.join_date,
        actor_id=current_user.id
    )
    return SingleResponse(data=emp)

@router.put(
    "/{id}",
    response_model=SingleResponse[Employee]
)
def update_employee(
    payload: EmployeeUpdate,
    emp_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_employees_manage")),
    service: EmployeeService = Depends(get_employee_service)
):
    emp = service.update_employee(
        uid=emp_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        avatar_url=payload.avatar_url,
        department_id=payload.department_id,
        role_id=payload.role_id,
        designation=payload.designation,
        status=payload.status,
        actor_id=current_user.id
    )
    return SingleResponse(data=emp)

@router.delete(
    "/{id}",
    status_code=204
)
def delete_employee(
    emp_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_employees_manage")),
    service: EmployeeService = Depends(get_employee_service)
):
    service.soft_delete_employee(emp_id, current_user.id)

@router.post(
    "/{id}/restore",
    response_model=SingleResponse[None]
)
def restore_employee(
    emp_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_employees_manage")),
    service: EmployeeService = Depends(get_employee_service)
):
    service.restore_employee(emp_id, current_user.id)
    return SingleResponse(data=None)
