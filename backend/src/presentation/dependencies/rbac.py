import time
from fastapi import Depends
from src.infrastructure.firestore.client import db
from src.presentation.dependencies.auth import get_current_employee
from src.domain.entities.employee import Employee
from src.shared.errors import ForbiddenError
from src.shared.logging import logger

# In-memory TTL cache mapping role_id -> (set_of_permission_keys, expiration_timestamp)
ROLE_PERMISSIONS_CACHE: dict[str, tuple[set[str], float]] = {}
CACHE_TTL_SECONDS = 300 # 5 minutes

def clear_role_cache(role_id: str | None = None) -> None:
    """Clear cached permissions for a specific role or all roles."""
    global ROLE_PERMISSIONS_CACHE
    if role_id:
        ROLE_PERMISSIONS_CACHE.pop(role_id, None)
        logger.info(f"Cleared permission cache for role: {role_id}")
    else:
        ROLE_PERMISSIONS_CACHE.clear()
        logger.info("Cleared entire permission cache")

def _get_resolved_permissions_for_role(role_id: str) -> set[str]:
    """Fetch role and resolve permission keys, caching the results."""
    now = time.time()
    cached_data = ROLE_PERMISSIONS_CACHE.get(role_id)
    
    if cached_data:
        keys, expires_at = cached_data
        if now < expires_at:
            return keys
            
    # Cache miss or expired - read from Firestore
    try:
        logger.info(f"Cache miss: Loading permissions for role: {role_id} from Firestore")
        role_ref = db.collection("roles").document(role_id)
        role_snap = role_ref.get()
        
        if not role_snap.exists:
            logger.warning(f"Role {role_id} not found in database")
            return set()
            
        role_data = role_snap.to_dict() or {}
        permission_ids = role_data.get("permissionIds", [])
        
        permission_keys = set()
        # Batch-read permissions or load them.
        # Since permissions is a small lookup collection, direct individual reads or batch is fine.
        # A firestore get_all is optimal for batch lookup.
        if permission_ids:
            perm_refs = [db.collection("permissions").document(pid) for pid in permission_ids]
            perm_snaps = db.get_all(perm_refs)
            for snap in perm_snaps:
                if snap.exists:
                    pdata = snap.to_dict() or {}
                    pkey = pdata.get("key")
                    if pkey:
                        permission_keys.add(pkey)
                        
        ROLE_PERMISSIONS_CACHE[role_id] = (permission_keys, now + CACHE_TTL_SECONDS)
        return permission_keys
        
    except Exception as e:
        logger.error(f"Error resolving permissions for role {role_id}: {e}")
        # Return empty set on failure to prevent security bypass
        return set()

def require_permission(permission_key: str):
    """
    Dependency factory to enforce role-based permission checks.
    Usage: Depends(require_permission("asset.create"))
    """
    async def dependency(employee: Employee = Depends(get_current_employee)) -> Employee:
        # Load and resolve permissions for the employee's role
        role_permissions = _get_resolved_permissions_for_role(employee.role_id)
        
        if permission_key not in role_permissions:
            logger.warning(
                f"Authorization failed: Employee {employee.id} (role: {employee.role_id}) lacks permission '{permission_key}'"
            )
            raise ForbiddenError(f"Insufficient permissions: required '{permission_key}'")
            
        return employee
        
    return dependency
