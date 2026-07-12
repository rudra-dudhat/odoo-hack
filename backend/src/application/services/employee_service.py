from datetime import datetime
from typing import Any
from fastapi import Depends
from src.domain.entities.employee import Employee
from src.domain.enums import EmployeeStatus, AuditLogAction
from src.domain.repositories.employee_repository import EmployeeRepository
from src.infrastructure.firestore.repositories.firestore_employee_repository import get_employee_repository
from src.domain.value_objects.snapshots import DepartmentSnapshot, RoleSnapshot
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.infrastructure.firestore.counters import get_next_employee_code
from src.infrastructure.auth.firebase_auth import sync_custom_claims
from src.shared.errors import NotFoundError, ConflictError, ValidationError
from src.shared.logging import logger

class EmployeeService:
    def __init__(
        self,
        employee_repo: EmployeeRepository,
        audit_log_service: AuditLogService
    ):
        self.employee_repo = employee_repo
        self.audit_log_service = audit_log_service

    def get_by_id(self, employee_id: str) -> Employee | None:
        return self.employee_repo.get_by_id(employee_id)

    def list_employees(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[Employee], str | None]:
        actual_sort_by = sort_by or "fullName"
        return self.employee_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def _sync_auth_claims(self, transaction, uid: str, role_id: str) -> None:
        """Helper to resolve role permissions and trigger async claims sync."""
        try:
            role_ref = db.collection("roles").document(role_id)
            role_snap = transaction.get(role_ref)
            if not role_snap.exists:
                return
                
            role_data = role_snap.to_dict() or {}
            permission_ids = role_data.get("permissionIds", [])
            
            permission_keys = []
            if permission_ids:
                perm_refs = [db.collection("permissions").document(pid) for pid in permission_ids]
                # For transaction reads, transaction.get() can accept a list of references!
                perm_snaps = transaction.get(perm_refs)
                for snap in perm_snaps:
                    if snap.exists:
                        pdata = snap.to_dict() or {}
                        pkey = pdata.get("key")
                        if pkey:
                            permission_keys.append(pkey)
                            
            # Trigger custom claims sync on the Firebase Auth user record
            sync_custom_claims(uid, role_id, permission_keys)
        except Exception as e:
            logger.error(f"Error syncing auth claims for employee {uid}: {e}")

    def create_employee(
        self,
        uid: str, # Pre-provisioned Firebase Auth UID
        full_name: str,
        email: str,
        phone: str,
        avatar_url: str | None,
        department_id: str,
        role_id: str,
        designation: str,
        join_date: datetime,
        actor_id: str
    ) -> Employee:
        
        def tx(transaction) -> Employee:
            # 1. Uniqueness check for email
            email_query = db.collection("employees").where("email", "==", email.lower()).where("isDeleted", "==", False).limit(1)
            email_snaps = email_query.get(transaction=transaction)
            if email_snaps:
                raise ConflictError(f"Employee with email '{email}' already exists")

            # 2. Verify and load department snapshot
            dept_ref = db.collection("departments").document(department_id)
            dept_snap = transaction.get(dept_ref)
            if not dept_snap.exists or dept_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Department {department_id} not found or is deleted")
            dept_data = dept_snap.to_dict() or {}
            dept_snapshot = DepartmentSnapshot(
                name=dept_data.get("name", ""),
                code=dept_data.get("code", "")
            )

            # 3. Verify and load role snapshot
            role_ref = db.collection("roles").document(role_id)
            role_snap = transaction.get(role_ref)
            if not role_snap.exists or role_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Role {role_id} not found or is deleted")
            role_data = role_snap.to_dict() or {}
            role_snapshot = RoleSnapshot(
                name=role_data.get("name", "")
            )

            # 4. Generate sequential employee code
            employee_code = get_next_employee_code(transaction)

            # 5. Build entity
            employee = Employee(
                id=uid,
                full_name=full_name,
                email=email.lower(),
                phone=phone,
                avatar_url=avatar_url,
                department_id=department_id,
                department_snapshot=dept_snapshot,
                role_id=role_id,
                role_snapshot=role_snapshot,
                designation=designation,
                employee_code=employee_code,
                join_date=join_date,
                status=EmployeeStatus.ACTIVE,
                created_by=actor_id,
                updated_by=actor_id
            )

            created_emp = self.employee_repo.create(employee)

            # 6. Log audit action
            self.audit_log_service.log_action(
                entity_type="employees",
                entity_id=uid,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=created_emp.model_dump(by_alias=True, exclude_none=True)
            )

            # 7. Sync custom claims to Firebase Auth
            self._sync_auth_claims(transaction, uid, role_id)
            
            return created_emp

        return run_in_transaction(tx)

    def update_employee(
        self,
        uid: str,
        full_name: str | None,
        email: str | None,
        phone: str | None,
        avatar_url: str | None,
        department_id: str | None,
        role_id: str | None,
        designation: str | None,
        status: EmployeeStatus | None,
        actor_id: str
    ) -> Employee:
        
        def tx(transaction) -> Employee:
            # 1. Fetch existing employee
            emp_ref = db.collection("employees").document(uid)
            emp_snap = transaction.get(emp_ref)
            if not emp_snap.exists or emp_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Employee {uid} not found")
                
            old_data = emp_snap.to_dict() or {}
            updates: dict[str, Any] = {}
            role_changed = False
            
            # 2. Parse updates & compile snapshots
            if full_name is not None:
                updates["fullName"] = full_name
            if email is not None and email.lower() != old_data.get("email"):
                email_query = db.collection("employees").where("email", "==", email.lower()).where("isDeleted", "==", False).limit(1)
                email_snaps = email_query.get(transaction=transaction)
                if email_snaps:
                    raise ConflictError(f"Employee with email '{email}' already exists")
                updates["email"] = email.lower()
            if phone is not None:
                updates["phone"] = phone
            if avatar_url is not None:
                updates["avatarUrl"] = avatar_url
            if designation is not None:
                updates["designation"] = designation
            if status is not None:
                updates["status"] = status.value
                
            if department_id is not None and department_id != old_data.get("departmentId"):
                dept_ref = db.collection("departments").document(department_id)
                dept_snap = transaction.get(dept_ref)
                if not dept_snap.exists or dept_snap.to_dict().get("isDeleted", False):
                    raise NotFoundError(f"Department {department_id} not found or is deleted")
                dept_data = dept_snap.to_dict() or {}
                updates["departmentId"] = department_id
                updates["departmentSnapshot"] = {
                    "name": dept_data.get("name", ""),
                    "code": dept_data.get("code", "")
                }
                
            if role_id is not None and role_id != old_data.get("roleId"):
                role_ref = db.collection("roles").document(role_id)
                role_snap = transaction.get(role_ref)
                if not role_snap.exists or role_snap.to_dict().get("isDeleted", False):
                    raise NotFoundError(f"Role {role_id} not found or is deleted")
                role_data = role_snap.to_dict() or {}
                updates["roleId"] = role_id
                updates["roleSnapshot"] = {
                    "name": role_data.get("name", "")
                }
                role_changed = True

            if not updates:
                old_data["id"] = emp_snap.id
                return Employee.model_validate(old_data)
                
            # Perform write
            updated_emp = self.employee_repo.update(uid, updates, actor_id)

            # Log audit action
            self.audit_log_service.log_action(
                entity_type="employees",
                entity_id=uid,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={k: old_data.get(k) for k in updates.keys()},
                after_snapshot={k: getattr(updated_emp, k, None) for k in updates.keys()}
            )

            # Sync claims if role changed
            if role_changed and role_id:
                self._sync_auth_claims(transaction, uid, role_id)
                
            return updated_emp

        return run_in_transaction(tx)

    def soft_delete_employee(self, uid: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            emp_ref = db.collection("employees").document(uid)
            emp_snap = transaction.get(emp_ref)
            if not emp_snap.exists or emp_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Employee {uid} not found")
                
            self.employee_repo.soft_delete(uid, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="employees",
                entity_id=uid,
                action=AuditLogAction.SOFT_DELETE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

    def restore_employee(self, uid: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            emp_ref = db.collection("employees").document(uid)
            emp_snap = transaction.get(emp_ref)
            if not emp_snap.exists:
                raise NotFoundError(f"Employee {uid} not found")
                
            self.employee_repo.restore(uid)
            self.employee_repo.update(uid, {}, actor_id) # Bump actor stamps
            
            self.audit_log_service.log_action(
                entity_type="employees",
                entity_id=uid,
                action=AuditLogAction.RESTORE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

def get_employee_service(
    employee_repo: EmployeeRepository = Depends(get_employee_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> EmployeeService:
    """Dependency injection factory for EmployeeService."""
    return EmployeeService(employee_repo, audit_log_service)
