from src.domain.entities.dashboard_aggregate import DashboardAggregate
from src.domain.repositories.dashboard_aggregate_repository import DashboardAggregateRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreDashboardAggregateRepository(BaseFirestoreRepository[DashboardAggregate], DashboardAggregateRepository):
    def __init__(self):
        super().__init__("dashboardAggregates", DashboardAggregate)

_repository_instance = None

def get_dashboard_aggregate_repository() -> DashboardAggregateRepository:
    """Dependency injection factory for DashboardAggregateRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreDashboardAggregateRepository()
    return _repository_instance
