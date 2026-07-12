from fastapi import APIRouter, Depends, Path
from src.application.dtos.base import SingleResponse
from src.application.dtos.dashboard import DashboardRecomputeRequest
from src.domain.entities.employee import Employee
from src.domain.entities.dashboard_aggregate import DashboardAggregate
from src.presentation.dependencies.rbac import require_permission
from src.application.services.dashboard_service import DashboardService, get_dashboard_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/{id}",
    response_model=SingleResponse[DashboardAggregate],
    dependencies=[Depends(require_permission("perm_dashboard_view"))]
)
def get_dashboard_aggregate(
    aggregate_id: str = Path(..., alias="id"),
    service: DashboardService = Depends(get_dashboard_service)
):
    agg = service.get_aggregate(aggregate_id)
    if not agg:
        raise NotFoundError(f"Dashboard aggregate '{aggregate_id}' not found")
    return SingleResponse(data=agg)

@router.post(
    "/recompute",
    response_model=SingleResponse[DashboardAggregate]
)
def recompute_dashboard_aggregate(
    payload: DashboardRecomputeRequest,
    current_user: Employee = Depends(require_permission("perm_departments_manage")),
    service: DashboardService = Depends(get_dashboard_service)
):
    agg = service.recompute_aggregate(
        scope=payload.scope,
        scope_ref_id=payload.scope_ref_id,
        actor_id=current_user.id
    )
    return SingleResponse(data=agg)
