from datetime import datetime
from typing import Any
from fastapi import Depends
from src.domain.entities.asset import Asset
from src.domain.entities.asset_category import AssetCategory
from src.domain.enums import AssetStatus, AssetCondition, AllocationStatus, DepreciationMethod, AuditLogAction
from src.domain.repositories.asset_repository import AssetRepository
from src.infrastructure.firestore.repositories.firestore_asset_repository import get_asset_repository
from src.domain.repositories.asset_category_repository import AssetCategoryRepository
from src.infrastructure.firestore.repositories.firestore_asset_category_repository import get_asset_category_repository
from src.domain.value_objects.snapshots import DepartmentSnapshot, AssetCategorySnapshot, CurrentHolderSnapshot
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.infrastructure.firestore.counters import get_next_asset_tag
from src.shared.errors import NotFoundError, ConflictError, ValidationError

class AssetService:
    def __init__(
        self,
        asset_repo: AssetRepository,
        category_repo: AssetCategoryRepository,
        audit_log_service: AuditLogService
    ):
        self.asset_repo = asset_repo
        self.category_repo = category_repo
        self.audit_log_service = audit_log_service

    # --- Asset Category Operations ---
    def get_category_by_id(self, category_id: str) -> AssetCategory | None:
        return self.category_repo.get_by_id(category_id)

    def list_categories(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[AssetCategory], str | None]:
        actual_sort_by = sort_by or "name"
        return self.category_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def create_category(
        self,
        name: str,
        code: str,
        description: str,
        parent_category_id: str | None,
        depreciation_method: DepreciationMethod,
        default_useful_life_months: int,
        actor_id: str
    ) -> AssetCategory:
        def tx(transaction) -> AssetCategory:
            # 1. Uniqueness check
            name_query = db.collection("assetCategories").where("name", "==", name).where("isDeleted", "==", False).limit(1)
            if name_query.get(transaction=transaction):
                raise ConflictError(f"Category with name '{name}' already exists")
                
            code_query = db.collection("assetCategories").where("code", "==", code.upper()).where("isDeleted", "==", False).limit(1)
            if code_query.get(transaction=transaction):
                raise ConflictError(f"Category with code '{code.upper()}' already exists")

            # 2. Hierarchy validation (Max 1 level deep)
            if parent_category_id:
                parent_ref = db.collection("assetCategories").document(parent_category_id)
                parent_snap = transaction.get(parent_ref)
                if not parent_snap.exists or parent_snap.to_dict().get("isDeleted", False):
                    raise NotFoundError(f"Parent category {parent_category_id} not found or is deleted")
                
                # Check parent doesn't have a parent (capping nesting depth)
                parent_data = parent_snap.to_dict() or {}
                if parent_data.get("parentCategoryId") is not None:
                    raise ValidationError("Nesting limit exceeded: Category hierarchy is capped at 1 level deep")

            # 3. Create
            cat = AssetCategory(
                name=name,
                code=code.upper(),
                description=description,
                parent_category_id=parent_category_id,
                depreciation_method=depreciation_method,
                default_useful_life_months=default_useful_life_months,
                created_by=actor_id,
                updated_by=actor_id
            )
            created_cat = self.category_repo.create(cat)
            
            # 4. Log
            self.audit_log_service.log_action(
                entity_type="assetCategories",
                entity_id=created_cat.id,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=created_cat.model_dump(by_alias=True, exclude_none=True)
            )
            return created_cat

        return run_in_transaction(tx)

    def update_category(
        self,
        category_id: str,
        name: str | None,
        description: str | None,
        parent_category_id: str | None,
        depreciation_method: DepreciationMethod | None,
        default_useful_life_months: int | None,
        actor_id: str
    ) -> AssetCategory:
        def tx(transaction) -> AssetCategory:
            cat_ref = db.collection("assetCategories").document(category_id)
            cat_snap = transaction.get(cat_ref)
            if not cat_snap.exists or cat_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Category {category_id} not found")
                
            old_data = cat_snap.to_dict() or {}
            updates: dict[str, Any] = {}
            
            if name is not None and name != old_data.get("name"):
                name_query = db.collection("assetCategories").where("name", "==", name).where("isDeleted", "==", False).limit(1)
                if name_query.get(transaction=transaction):
                    raise ConflictError(f"Category with name '{name}' already exists")
                updates["name"] = name
                
            if description is not None:
                updates["description"] = description
                
            if parent_category_id is not None and parent_category_id != old_data.get("parentCategoryId"):
                parent_ref = db.collection("assetCategories").document(parent_category_id)
                parent_snap = transaction.get(parent_ref)
                if not parent_snap.exists or parent_snap.to_dict().get("isDeleted", False):
                    raise NotFoundError(f"Parent category {parent_category_id} not found or is deleted")
                
                # Check hierarchy depth
                parent_data = parent_snap.to_dict() or {}
                if parent_data.get("parentCategoryId") is not None:
                    raise ValidationError("Nesting limit exceeded: Category hierarchy is capped at 1 level deep")
                updates["parentCategoryId"] = parent_category_id
            elif parent_category_id is None and "parentCategoryId" in old_data:
                # Clear parent
                updates["parentCategoryId"] = None
                
            if depreciation_method is not None:
                updates["depreciationMethod"] = depreciation_method.value
            if default_useful_life_months is not None:
                updates["defaultUsefulLifeMonths"] = default_useful_life_months
                
            if not updates:
                old_data["id"] = cat_snap.id
                return AssetCategory.model_validate(old_data)
                
            updated_cat = self.category_repo.update(category_id, updates, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="assetCategories",
                entity_id=category_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={k: old_data.get(k) for k in updates.keys()},
                after_snapshot={k: getattr(updated_cat, k, None) for k in updates.keys()}
            )
            return updated_cat

        return run_in_transaction(tx)

    def soft_delete_category(self, category_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            cat_ref = db.collection("assetCategories").document(category_id)
            cat_snap = transaction.get(cat_ref)
            if not cat_snap.exists or cat_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Category {category_id} not found")
                
            cat_data = cat_snap.to_dict() or {}
            asset_count = cat_data.get("assetCount", 0)
            
            if asset_count > 0:
                raise ConflictError(f"Category cannot be deleted: it contains {asset_count} assets")
                
            self.category_repo.soft_delete(category_id, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="assetCategories",
                entity_id=category_id,
                action=AuditLogAction.SOFT_DELETE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

    def restore_category(self, category_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            cat_ref = db.collection("assetCategories").document(category_id)
            cat_snap = transaction.get(cat_ref)
            if not cat_snap.exists:
                raise NotFoundError(f"Category {category_id} not found")
                
            self.category_repo.restore(category_id)
            self.category_repo.update(category_id, {}, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="assetCategories",
                entity_id=category_id,
                action=AuditLogAction.RESTORE,
                performed_by=actor_id
            )

        run_in_transaction(tx)


    # --- Asset Operations ---
    def get_asset_by_id(self, asset_id: str) -> Asset | None:
        return self.asset_repo.get_by_id(asset_id)

    def list_assets(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[Asset], str | None]:
        actual_sort_by = sort_by or "assetTag"
        return self.asset_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def create_asset(
        self,
        name: str,
        category_id: str,
        department_id: str,
        serial_number: str,
        manufacturer: str,
        model: str,
        purchase_date: datetime | None,
        purchase_cost: int,
        currency: str,
        warranty_expiry_date: datetime | None,
        location: str,
        image_urls: list[str],
        condition: AssetCondition,
        actor_id: str
    ) -> Asset:
        def tx(transaction) -> Asset:
            # 1. Fetch category & compile snapshot
            cat_ref = db.collection("assetCategories").document(category_id)
            cat_snap = transaction.get(cat_ref)
            if not cat_snap.exists or cat_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Category {category_id} not found or is deleted")
            cat_data = cat_snap.to_dict() or {}
            category_snapshot = AssetCategorySnapshot(
                name=cat_data.get("name", ""),
                code=cat_data.get("code", "")
            )

            # 2. Fetch department & compile snapshot
            dept_ref = db.collection("departments").document(department_id)
            dept_snap = transaction.get(dept_ref)
            if not dept_snap.exists or dept_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Department {department_id} not found or is deleted")
            dept_data = dept_snap.to_dict() or {}
            department_snapshot = DepartmentSnapshot(
                name=dept_data.get("name", ""),
                code=dept_data.get("code", "")
            )

            # 3. Generate sequential Asset Tag
            asset_tag = get_next_asset_tag(transaction)

            # 4. Construct asset
            asset = Asset(
                id=asset_tag,
                asset_tag=asset_tag,
                name=name,
                category_id=category_id,
                category_snapshot=category_snapshot,
                department_id=department_id,
                department_snapshot=department_snapshot,
                serial_number=serial_number,
                manufacturer=manufacturer,
                model=model,
                purchase_date=purchase_date,
                purchase_cost=purchase_cost,
                currency=currency.upper(),
                warranty_expiry_date=warranty_expiry_date,
                location=location,
                image_urls=image_urls,
                status=AssetStatus.AVAILABLE,
                condition=condition,
                created_by=actor_id,
                updated_by=actor_id
            )
            created_asset = self.asset_repo.create(asset)

            # 5. Log audit log
            self.audit_log_service.log_action(
                entity_type="assets",
                entity_id=asset_tag,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=created_asset.model_dump(by_alias=True, exclude_none=True)
            )
            return created_asset

        return run_in_transaction(tx)

    def update_asset(
        self,
        asset_id: str,
        name: str | None,
        category_id: str | None,
        department_id: str | None,
        serial_number: str | None,
        manufacturer: str | None,
        model: str | None,
        purchase_date: datetime | None,
        purchase_cost: int | None,
        currency: str | None,
        warranty_expiry_date: datetime | None,
        location: str | None,
        image_urls: list[str] | None,
        condition: AssetCondition | None,
        actor_id: str
    ) -> Asset:
        def tx(transaction) -> Asset:
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if not asset_snap.exists or asset_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Asset {asset_id} not found")
                
            old_data = asset_snap.to_dict() or {}
            updates: dict[str, Any] = {}
            
            if name is not None:
                updates["name"] = name
            if serial_number is not None:
                updates["serialNumber"] = serial_number
            if manufacturer is not None:
                updates["manufacturer"] = manufacturer
            if model is not None:
                updates["model"] = model
            if purchase_date is not None:
                updates["purchaseDate"] = purchase_date
            if purchase_cost is not None:
                updates["purchaseCost"] = purchase_cost
            if currency is not None:
                updates["currency"] = currency.upper()
            if warranty_expiry_date is not None:
                updates["warrantyExpiryDate"] = warranty_expiry_date
            if location is not None:
                updates["location"] = location
            if image_urls is not None:
                updates["imageUrls"] = image_urls
            if condition is not None:
                updates["condition"] = condition.value
                
            if category_id is not None and category_id != old_data.get("categoryId"):
                cat_ref = db.collection("assetCategories").document(category_id)
                cat_snap = transaction.get(cat_ref)
                if not cat_snap.exists or cat_snap.to_dict().get("isDeleted", False):
                    raise NotFoundError(f"Category {category_id} not found or is deleted")
                cat_data = cat_snap.to_dict() or {}
                updates["categoryId"] = category_id
                updates["categorySnapshot"] = {
                    "name": cat_data.get("name", ""),
                    "code": cat_data.get("code", "")
                }
                
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

            if not updates:
                old_data["id"] = asset_snap.id
                return Asset.model_validate(old_data)
                
            updated_asset = self.asset_repo.update(asset_id, updates, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="assets",
                entity_id=asset_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={k: old_data.get(k) for k in updates.keys()},
                after_snapshot={k: getattr(updated_asset, k, None) for k in updates.keys()}
            )
            return updated_asset

        return run_in_transaction(tx)

    def _force_close_allocation(self, transaction, allocation_id: str, new_status: AllocationStatus, note: str, condition: AssetCondition | None = None) -> None:
        """Helper to transition allocation status inside a transaction."""
        alloc_ref = db.collection("assetAllocations").document(allocation_id)
        updates = {
            "status": new_status.value,
            "returnedAt": firestore.SERVER_TIMESTAMP,
            "notes": f"[FORCE CLOSED] {note}"
        }
        if condition:
            updates["conditionAtReturn"] = condition.value
            
        transaction.update(alloc_ref, updates)

    def retire_asset(self, asset_id: str, note: str, actor_id: str) -> Asset:
        def tx(transaction) -> Asset:
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if not asset_snap.exists or asset_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Asset {asset_id} not found")
                
            asset_data = asset_snap.to_dict() or {}
            current_status = asset_data.get("status")
            if current_status in (AssetStatus.RETIRED, AssetStatus.LOST):
                raise ConflictError(f"Asset is already in '{current_status}' state")
                
            allocation_id = asset_data.get("currentAllocationId")
            
            updates = {
                "status": AssetStatus.RETIRED.value,
                "currentAllocationId": None,
                "currentHolderSnapshot": None
            }
            
            # Force close active allocation if present
            if allocation_id:
                self._force_close_allocation(
                    transaction=transaction,
                    allocation_id=allocation_id,
                    new_status=AllocationStatus.RETURNED,
                    note=note,
                    condition=AssetCondition(asset_data.get("condition", "good"))
                )
                
            updated_asset = self.asset_repo.update(asset_id, updates, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="assets",
                entity_id=asset_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": current_status, "currentAllocationId": allocation_id},
                after_snapshot={"status": AssetStatus.RETIRED.value, "currentAllocationId": None}
            )
            return updated_asset

        return run_in_transaction(tx)

    def report_lost_asset(self, asset_id: str, note: str, actor_id: str) -> Asset:
        def tx(transaction) -> Asset:
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if not asset_snap.exists or asset_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Asset {asset_id} not found")
                
            asset_data = asset_snap.to_dict() or {}
            current_status = asset_data.get("status")
            if current_status in (AssetStatus.RETIRED, AssetStatus.LOST):
                raise ConflictError(f"Asset is already in '{current_status}' state")
                
            allocation_id = asset_data.get("currentAllocationId")
            
            updates = {
                "status": AssetStatus.LOST.value,
                "currentAllocationId": None,
                "currentHolderSnapshot": None
            }
            
            # Force close active allocation if present
            if allocation_id:
                self._force_close_allocation(
                    transaction=transaction,
                    allocation_id=allocation_id,
                    new_status=AllocationStatus.LOST,
                    note=note
                )
                
            updated_asset = self.asset_repo.update(asset_id, updates, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="assets",
                entity_id=asset_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": current_status, "currentAllocationId": allocation_id},
                after_snapshot={"status": AssetStatus.LOST.value, "currentAllocationId": None}
            )
            return updated_asset

        return run_in_transaction(tx)

    def soft_delete_asset(self, asset_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if not asset_snap.exists or asset_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Asset {asset_id} not found")
                
            asset_data = asset_snap.to_dict() or {}
            status = asset_data.get("status")
            allocation_id = asset_data.get("currentAllocationId")
            
            # Restrict soft delete to retired/lost assets without active allocations
            if status not in (AssetStatus.RETIRED, AssetStatus.LOST) or allocation_id is not None:
                raise ConflictError(
                    f"Asset cannot be deleted: status must be 'retired' or 'lost' and cannot have active allocations (Current status: {status})"
                )
                
            self.asset_repo.soft_delete(asset_id, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="assets",
                entity_id=asset_id,
                action=AuditLogAction.SOFT_DELETE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

    def restore_asset(self, asset_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if not asset_snap.exists:
                raise NotFoundError(f"Asset {asset_id} not found")
                
            self.asset_repo.restore(asset_id)
            self.asset_repo.update(asset_id, {}, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="assets",
                entity_id=asset_id,
                action=AuditLogAction.RESTORE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

def get_asset_service(
    asset_repo: AssetRepository = Depends(get_asset_repository),
    category_repo: AssetCategoryRepository = Depends(get_asset_category_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> AssetService:
    """Dependency injection factory for AssetService."""
    return AssetService(asset_repo, category_repo, audit_log_service)
