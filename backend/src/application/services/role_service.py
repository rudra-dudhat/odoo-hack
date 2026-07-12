from typing import Any
from fastapi import Depends
from src.domain.entities.role import Role
from src.domain.enums import AuditLogAction
from src.domain.repositories.role_repository import RoleRepository
from src.infrastructure.firestore.repositories.firestore_role_repository import get_role_repository
from src.domain.repositories.permission_repository import PermissionRepository
from src.infrastructure.firestore.repositories.firestore_permission_repository import get_permission_repository
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.infrastructure.auth.firebase_auth import sync_custom_claims
from src.shared.errors import NotFoundError, ConflictError
from src.shared.logging import logger

class RoleService:
    def __init__(
        self,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        audit_log_service: AuditLogService
    ):
        self.role_repo = role_repo
        self.permission_repo = permission_repo
        self.audit_log_service = audit_log_service

    def get_role_by_id(self, role_id: str) -> Role | None:
        return self.role_repo.get_by_id(role_id)

    def list_roles(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[Role], str | None]:
        actual_sort_by = sort_by or "name"
        return self.role_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def _sync_role_claims_for_employees(self, transaction, role_id: str, permission_keys: list[str]) -> None:
        """Fetch all employees holding the role and update their Firebase claims."""
        try:
            # Query active employees matching roleId
            emp_query = db.collection("employees").where("roleId", "==", role_id).where("isDeleted", "==", False)
            emp_snaps = emp_query.get(transaction=transaction)
            
            for snap in emp_snaps:
                uid = snap.id
                sync_custom_claims(uid, role_id, permission_keys)
        except Exception as e:
            logger.error(f"Failed to propagate custom claims for role {role_id}: {e}")

    def create_role(
        self,
        role_id: str, # Controlled slug like 'role_manager'
        name: str,
        description: str,
        permission_ids: list[str],
        actor_id: str
    ) -> Role:
        def tx(transaction) -> Role:
            # 1. Uniqueness check
            name_query = db.collection("roles").where("name", "==", name).where("isDeleted", "==", False).limit(1)
            name_snaps = name_query.get(transaction=transaction)
            if name_snaps:
                raise ConflictError(f"Role with name '{name}' already exists")
                
            role_ref = db.collection("roles").document(role_id)
            if transaction.get(role_ref).exists:
                raise ConflictError(f"Role ID '{role_id}' already exists")

            # 2. Check permission existence
            permission_keys = []
            if permission_ids:
                perm_refs = [db.collection("permissions").document(pid) for pid in permission_ids]
                perm_snaps = transaction.get(perm_refs)
                for i, snap in enumerate(perm_snaps):
                    if not snap.exists or snap.to_dict().get("isDeleted", False):
                        raise NotFoundError(f"Permission with ID '{permission_ids[i]}' not found or is deleted")
                    pdata = snap.to_dict() or {}
                    pkey = pdata.get("key")
                    if pkey:
                        permission_keys.add(pkey) if isinstance(permission_keys, set) else permission_keys.append(pkey)

            # 3. Create role
            role = Role(
                id=role_id,
                name=name,
                description=description,
                permission_ids=permission_ids,
                is_system_role=False,
                created_by=actor_id,
                updated_by=actor_id
            )
            created_role = self.role_repo.create(role)
            
            # 4. Audit logging
            self.audit_log_service.log_action(
                entity_type="roles",
                entity_id=role_id,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=created_role.model_dump(by_alias=True, exclude_none=True)
            )
            return created_role

        return run_in_transaction(tx)

    def update_role(
        self,
        role_id: str,
        name: str | None,
        description: str | None,
        permission_ids: list[str] | None,
        actor_id: str
    ) -> Role:
        def tx(transaction) -> Role:
            # 1. Fetch existing role
            role_ref = db.collection("roles").document(role_id)
            role_snap = transaction.get(role_ref)
            if not role_snap.exists or role_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Role {role_id} not found")
                
            old_data = role_snap.to_dict() or {}
            is_system_role = old_data.get("isSystemRole", False)
            
            updates: dict[str, Any] = {}
            permissions_changed = False
            permission_keys = []
            
            if name is not None and name != old_data.get("name"):
                if is_system_role:
                    raise ConflictError("System role names are immutable")
                name_query = db.collection("roles").where("name", "==", name).where("isDeleted", "==", False).limit(1)
                name_snaps = name_query.get(transaction=transaction)
                if name_snaps:
                    raise ConflictError(f"Role with name '{name}' already exists")
                updates["name"] = name
                
            if description is not None:
                updates["description"] = description
                
            if permission_ids is not None:
                # Enforce verification of all permission references
                if permission_ids:
                    perm_refs = [db.collection("permissions").document(pid) for pid in permission_ids]
                    perm_snaps = transaction.get(perm_refs)
                    for i, snap in enumerate(perm_snaps):
                        if not snap.exists or snap.to_dict().get("isDeleted", False):
                            raise NotFoundError(f"Permission with ID '{permission_ids[i]}' not found or is deleted")
                        pdata = snap.to_dict() or {}
                        pkey = pdata.get("key")
                        if pkey:
                            permission_keys.append(pkey)
                            
                updates["permissionIds"] = permission_ids
                permissions_changed = True

            if not updates:
                old_data["id"] = role_snap.id
                return Role.model_validate(old_data)

            # Perform write
            updated_role = self.role_repo.update(role_id, updates, actor_id)

            # Log audit
            self.audit_log_service.log_action(
                entity_type="roles",
                entity_id=role_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={k: old_data.get(k) for k in updates.keys()},
                after_snapshot={k: getattr(updated_role, k, None) for k in updates.keys()}
            )

            # Trigger Firebase claims sync for all employees holding this role
            if permissions_changed:
                self._sync_role_claims_for_employees(transaction, role_id, permission_keys)
                
            return updated_role

        return run_in_transaction(tx)

    def soft_delete_role(self, role_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            # 1. Fetch role
            role_ref = db.collection("roles").document(role_id)
            role_snap = transaction.get(role_ref)
            if not role_snap.exists or role_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Role {role_id} not found")
                
            role_data = role_snap.to_dict() or {}
            
            # 2. Block system role deletion
            if role_data.get("isSystemRole", False):
                raise ConflictError("System roles cannot be deleted")
                
            # 3. Block deletion if role is currently assigned to active employees
            emp_query = db.collection("employees").where("roleId", "==", role_id).where("isDeleted", "==", False).limit(1)
            emp_snaps = emp_query.get(transaction=transaction)
            if emp_snaps:
                raise ConflictError(f"Role '{role_id}' cannot be deleted: it is currently assigned to active employees")

            # 4. Perform soft delete
            self.role_repo.soft_delete(role_id, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="roles",
                entity_id=role_id,
                action=AuditLogAction.SOFT_DELETE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

    def restore_role(self, role_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            role_ref = db.collection("roles").document(role_id)
            role_snap = transaction.get(role_ref)
            if not role_snap.exists:
                raise NotFoundError(f"Role {role_id} not found")
                
            self.role_repo.restore(role_id)
            self.role_repo.update(role_id, {}, actor_id) # Actor stamp bump
            
            self.audit_log_service.log_action(
                entity_type="roles",
                entity_id=role_id,
                action=AuditLogAction.RESTORE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

def get_role_service(
    role_repo: RoleRepository = Depends(get_role_repository),
    permission_repo: PermissionRepository = Depends(get_permission_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> RoleService:
    """Dependency injection factory for RoleService."""
    return RoleService(role_repo, permission_repo, audit_log_service)
