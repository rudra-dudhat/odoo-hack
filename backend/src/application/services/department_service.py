from typing import Any
from fastapi import Depends
from src.domain.entities.department import Department
from src.domain.enums import DepartmentStatus, AuditLogAction
from src.domain.repositories.department_repository import DepartmentRepository
from src.infrastructure.firestore.repositories.firestore_department_repository import get_department_repository
from src.domain.repositories.employee_repository import EmployeeRepository
from src.infrastructure.firestore.repositories.firestore_employee_repository import get_employee_repository
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.shared.errors import NotFoundError, ConflictError, ValidationError

class DepartmentService:
    def __init__(
        self,
        dept_repo: DepartmentRepository,
        employee_repo: EmployeeRepository,
        audit_log_service: AuditLogService
    ):
        self.dept_repo = dept_repo
        self.employee_repo = employee_repo
        self.audit_log_service = audit_log_service

    def get_by_id(self, dept_id: str) -> Department | None:
        return self.dept_repo.get_by_id(dept_id)

    def list_departments(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[Department], str | None]:
        actual_sort_by = sort_by or "name"
        return self.dept_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def create_department(self, name: str, code: str, description: str, head_employee_id: str | None, actor_id: str) -> Department:
        # Enforce uniqueness and head employee existence checks inside a transaction
        def tx(transaction) -> Department:
            # 1. Uniqueness check for name & code
            name_query = db.collection("departments").where("name", "==", name).where("isDeleted", "==", False).limit(1)
            name_snaps = name_query.get(transaction=transaction)
            if name_snaps:
                raise ConflictError(f"Department with name '{name}' already exists")
                
            code_query = db.collection("departments").where("code", "==", code.upper()).where("isDeleted", "==", False).limit(1)
            code_snaps = code_query.get(transaction=transaction)
            if code_snaps:
                raise ConflictError(f"Department with code '{code.upper()}' already exists")
                
            # 2. Check head employee existence if set
            if head_employee_id:
                emp_ref = db.collection("employees").document(head_employee_id)
                emp_snap = transaction.get(emp_ref)
                if not emp_snap.exists or emp_snap.to_dict().get("isDeleted", False):
                    raise NotFoundError(f"Head employee with ID {head_employee_id} not found or is deleted")

            # 3. Create entity
            dept = Department(
                name=name,
                code=code.upper(),
                description=description,
                head_employee_id=head_employee_id,
                status=DepartmentStatus.ACTIVE,
                created_by=actor_id,
                updated_by=actor_id
            )
            
            created_dept = self.dept_repo.create(dept)
            
            # 4. Log audit action
            self.audit_log_service.log_action(
                entity_type="departments",
                entity_id=created_dept.id,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=created_dept.model_dump(by_alias=True, exclude_none=True)
            )
            return created_dept

        return run_in_transaction(tx)

    def update_department(
        self,
        dept_id: str,
        name: str | None,
        description: str | None,
        head_employee_id: str | None,
        status: DepartmentStatus | None,
        actor_id: str
    ) -> Department:
        def tx(transaction) -> Department:
            # 1. Fetch existing department
            dept_ref = db.collection("departments").document(dept_id)
            dept_snap = transaction.get(dept_ref)
            if not dept_snap.exists or dept_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Department {dept_id} not found")
                
            old_data = dept_snap.to_dict() or {}
            
            # 2. Perform validation if updating name
            updates: dict[str, Any] = {}
            if name is not None and name != old_data.get("name"):
                name_query = db.collection("departments").where("name", "==", name).where("isDeleted", "==", False).limit(1)
                name_snaps = name_query.get(transaction=transaction)
                if name_snaps:
                    raise ConflictError(f"Department with name '{name}' already exists")
                updates["name"] = name
                
            if description is not None:
                updates["description"] = description
                
            if head_employee_id is not None and head_employee_id != old_data.get("headEmployeeId"):
                emp_ref = db.collection("employees").document(head_employee_id)
                emp_snap = transaction.get(emp_ref)
                if not emp_snap.exists or emp_snap.to_dict().get("isDeleted", False):
                    raise NotFoundError(f"Head employee with ID {head_employee_id} not found or is deleted")
                updates["headEmployeeId"] = head_employee_id
            elif head_employee_id is None and "headEmployeeId" in old_data:
                # To clear head employee, client might pass head_employee_id = None explicitly
                updates["headEmployeeId"] = None
                
            if status is not None:
                updates["status"] = status.value
                
            if not updates:
                # Return current state if no updates provided
                old_data["id"] = dept_snap.id
                return Department.model_validate(old_data)
                
            # Perform update
            updated_dept = self.dept_repo.update(dept_id, updates, actor_id)
            
            # Log audit action
            self.audit_log_service.log_action(
                entity_type="departments",
                entity_id=dept_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={k: old_data.get(k) for k in updates.keys()},
                after_snapshot={k: getattr(updated_dept, k, None) for k in updates.keys()}
            )
            return updated_dept

        return run_in_transaction(tx)

    def soft_delete_department(self, dept_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            # 1. Fetch existing department
            dept_ref = db.collection("departments").document(dept_id)
            dept_snap = transaction.get(dept_ref)
            if not dept_snap.exists or dept_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Department {dept_id} not found")
                
            data = dept_snap.to_dict() or {}
            employee_count = data.get("employeeCount", 0)
            asset_count = data.get("assetCount", 0)
            
            # 2. Block delete if department still has active employees or assets
            if employee_count > 0 or asset_count > 0:
                raise ConflictError(
                    f"Department cannot be deleted: contains {employee_count} active employees and {asset_count} assets"
                )
                
            # 3. Perform soft delete
            self.dept_repo.soft_delete(dept_id, actor_id)
            
            # 4. Log audit action
            self.audit_log_service.log_action(
                entity_type="departments",
                entity_id=dept_id,
                action=AuditLogAction.SOFT_DELETE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

    def restore_department(self, dept_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            dept_ref = db.collection("departments").document(dept_id)
            dept_snap = transaction.get(dept_ref)
            if not dept_snap.exists:
                raise NotFoundError(f"Department {dept_id} not found")
                
            self.dept_repo.restore(dept_id)
            self.dept_repo.update(dept_id, {}, actor_id) # Set actor stamp
            
            self.audit_log_service.log_action(
                entity_type="departments",
                entity_id=dept_id,
                action=AuditLogAction.RESTORE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

def get_department_service(
    dept_repo: DepartmentRepository = Depends(get_department_repository),
    employee_repo: EmployeeRepository = Depends(get_employee_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> DepartmentService:
    """Dependency injection factory for DepartmentService."""
    return DepartmentService(dept_repo, employee_repo, audit_log_service)
